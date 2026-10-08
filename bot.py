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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8529227386:AAFsqpj5mq4N_fRq1MJ9_hwF-hir7bVGrxw")

SESSION_STRING = "BQJHHrsAQohDxth8QaB1QzlGPlg2cO1cI-q5Viul5T2qLYszFLakA-2qWY0Bk21lr6dURBASZV3i98pBNIWxlCehYAAckAlk3grALwFyBq-D4cwX2jVOADnnZxcdo0GcAw4pdJdDR1Zdj4SVk8kfOvrEOtzio5fp16gbcFGVMX8tPrXPyNA4TVyg6NbWSayKzMp-pqPsywpR5Ii9OOqf4nGOE9MsZsZgXU3sOkz--DUqOT0HBkVBLFHHnmX1D_RE9PS00My9cfd0cgxszhCB7KWjT9tkpGEEM3UKgY9gksoy3behq2dcrew-negn2aY-s52ynWP1t0Xr6_MbzbcU0Y7zvg9MUAAAAAEuegsXAA"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://nveowfitvoligqecxofr.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_fqZzvMNKkcupSdiGMEtebA_J_UK9z9F")

# Logging setup
logging.basicConfig(level=logging.INFO)

# Get internal FFmpeg executable path automatically
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

# 1️⃣ MAIN BOT CLIENT INITIALIZE
app = Client(
    "Kage_x_Bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# 2️⃣ USERBOT CLIENT INITIALIZE
userbot = None
if SESSION_STRING and len(SESSION_STRING) > 20:
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
USER_BANNERS = {}
WAITING_FOR_CLONE_TOKEN = set()

@app.on_message(filters.command("start"))
async def start_command(client, message):
    username = message.from_user.username or message.from_user.first_name

    menu_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📁 My Files / Hub", callback_data="my_files"),
            InlineKeyboardButton("📥 Downloader", callback_data="downloader")
        ],
        [
            InlineKeyboardButton("🗜️ Video Compressor Studio", callback_data="compress_menu"),
            InlineKeyboardButton("🖼️ Set Custom Thumbnail", callback_data="set_banner_menu")
        ],
        [
            InlineKeyboardButton("🤖 Create My Own Clone", callback_data="clone_menu"),
            InlineKeyboardButton("💎 Premium", callback_data="premium")
        ]
    ])

    await message.reply_text(
        f"👋 **Hello {username}!**\n\n"
        f"Welcome to **Kage x Bot** 🚀\n"
        f"👑 **Developer:** @kage_x_edit\n\n"
        f"Neeche diye gaye buttons se features explore karein:",
        reply_markup=menu_keyboard
    )

@app.on_callback_query(filters.regex("compress_menu"))
async def compress_menu(client, callback_query):
    await callback_query.message.edit_text(
        "🗜 **Video Compressor Studio**\n"
        "👑 **Developer:** @kage_x_edit\n\n"
        "Bhai, apni video yahan direct bhej do. Bot 360p, 720p, 1080p aur All-in-3 options mein heavy compression ke sath file dega!",
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
    status_text = "🟢 **Custom thumbnail saved hai!**" if has_banner else "🔴 **Koi thumbnail saved nahi hai.**"
    
    await callback_query.message.edit_text(
        f"🖼 **Custom Thumbnail Setup (Full HD)**\n\n{status_text}\n\nApni HD Thumbnail/Logo image yahan bhej do!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_menu")]])
    )

@app.on_callback_query(filters.regex("back_to_menu"))
async def back_to_menu(client, callback_query):
    user_id = callback_query.from_user.id
    USER_SETTING_BANNER.discard(user_id)
    WAITING_FOR_CLONE_TOKEN.discard(user_id)
        
    menu_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📁 My Files / Hub", callback_data="my_files"),
            InlineKeyboardButton("📥 Downloader", callback_data="downloader")
        ],
        [
            InlineKeyboardButton("🗜️ Video Compressor Studio", callback_data="compress_menu"),
            InlineKeyboardButton("🖼️ Set Custom Thumbnail", callback_data="set_banner_menu")
        ],
        [
            InlineKeyboardButton("🤖 Create My Own Clone", callback_data="clone_menu"),
            InlineKeyboardButton("💎 Premium", callback_data="premium")
        ]
    ])
    await callback_query.message.edit_text(
        "👋 **Main Menu**\n👑 **Developer:** @kage_x_edit\n\nNeeche diye gaye buttons se features explore karein:",
        reply_markup=menu_keyboard
    )

# 📥 RESTRICTED LINK DOWNLOADER HANDLER
@app.on_message(filters.regex(r"https?://t\.me/(?:c/)?([a-zA-Z0-9_]+)/(\d+)") & filters.private)
async def restricted_link_handler(client, message):
    if not userbot:
        await message.reply_text("❌ Restricted downloader ke liye `SESSION_STRING` configured nahi hai!")
        return

    link = message.text.strip()
    match = re.search(r"t\.me/(?:c/)?([a-zA-Z0-9_]+)/(\d+)", link)
    if not match:
        return
        
    chat_identifier = match.group(1)
    msg_id = int(match.group(2))
    chat_id = int("-100" + chat_identifier) if chat_identifier.isdigit() else "@" + chat_identifier
        
    progress_msg = await message.reply_text("📥 **Connecting & Fetching content...**")

    try:
        try:
            await userbot.get_chat(chat_id)
        except Exception:
            try:
                await userbot.join_chat(chat_identifier if not chat_identifier.isdigit() else int("-100" + chat_identifier))
            except Exception:
                pass

        target_msg = await userbot.get_messages(chat_id, msg_id)
        if not target_msg or target_msg.empty:
            await progress_msg.edit("❌ Ye message nahi mila ya channel private/restricted hai!")
            return
            
        if target_msg.media:
            file_path = await target_msg.download()
            await progress_msg.edit("📤 **Uploading to your chat...**")
            
            if target_msg.video:
                thumb_path = None
                if target_msg.video.thumbs:
                    try:
                        thumb_path = await userbot.download_media(target_msg.video.thumbs[0].file_id)
                    except Exception:
                        pass
                
                await client.send_video(
                    chat_id=message.chat.id, video=file_path, thumb=thumb_path,
                    duration=target_msg.video.duration, width=target_msg.video.width,
                    height=target_msg.video.height, supports_streaming=True, caption=target_msg.caption or ""
                )
                if thumb_path and os.path.exists(thumb_path):
                    os.remove(thumb_path)
            elif target_msg.document:
                await client.send_document(chat_id=message.chat.id, document=file_path, caption=target_msg.caption or "")
            elif target_msg.photo:
                await client.send_photo(chat_id=message.chat.id, photo=file_path, caption=target_msg.caption or "")
            
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        else:
            await client.send_message(chat_id=message.chat.id, text=target_msg.text or "")
            
        await progress_msg.delete()
    except Exception as e:
        await progress_msg.edit(f"❌ Error aagaya bhai: `{str(e)}`")

@app.on_message(filters.photo & filters.private)
async def receive_photo(client, message):
    user_id = message.from_user.id
    if user_id in USER_SETTING_BANNER:
        USER_SETTING_BANNER.remove(user_id)
        banner_path = f"banner_{user_id}.png"
        downloaded_banner = await message.download(file_name=banner_path)
        USER_BANNERS[user_id] = downloaded_banner or banner_path
        
        await message.reply_text(
            "✅ **Full HD Thumbnail Saved Successfully!**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_menu")]])
        )

# 🎬 RECEIVE VIDEO & SHOW QUALITY OPTIONS DIRECTLY
@app.on_message((filters.video | filters.document) & filters.private)
async def receive_video_for_compression(client, message):
    user_id = message.from_user.id
    if message.document and not message.document.mime_type.startswith("video"):
        return

    USER_VIDEOS[user_id] = message

    quality_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📉 360p (Ultra Low MB)", callback_data="comp_360p"),
            InlineKeyboardButton("📊 720p (Balanced)", callback_data="comp_720p")
        ],
        [
            InlineKeyboardButton("📈 1080p (HD Compressed)", callback_data="comp_1080p"),
            InlineKeyboardButton("🔥 All in 3 Qualities (360+720+1080)", callback_data="comp_all")
        ]
    ])

    file_name = "video.mp4"
    if message.video and message.video.file_name:
        file_name = message.video.file_name
    elif message.document and message.document.file_name:
        file_name = message.document.file_name

    await message.reply_text(
        f"🎬 **Video Received!**\n"
        f"📁 File: `{file_name}`\n\n"
        f"Select compression quality to reduce MB/GB instantly:",
        reply_markup=quality_keyboard
    )

# ⚙️ COMPRESSION & FULL HD OVERLAY PROCESSOR
async def compress_and_send(client, callback_query, mode):
    user_id = callback_query.from_user.id
    if user_id not in USER_VIDEOS:
        await callback_query.answer("⚠ Session expired! Dubara video bhejo.", show_alert=True)
        return

    msg = USER_VIDEOS[user_id]
    original_name = "video.mp4"
    if msg.video and msg.video.file_name:
        original_name = msg.video.file_name
    elif msg.document and msg.document.file_name:
        original_name = msg.document.file_name

    status_msg = await callback_query.message.edit_text("📥 **Downloading video for heavy compression...**")
    
    input_file = f"input_{user_id}.mp4"
    banner_file = USER_BANNERS.get(user_id, f"banner_{user_id}.png")
    
    try:
        downloaded_path = await msg.download(file_name=input_file)
        has_banner = os.path.exists(banner_file)
        
        qualities_to_process = []
        if mode == "comp_360p":
            qualities_to_process = [("360p", "scale=-2:360", "28")]
        elif mode == "comp_720p":
            qualities_to_process = [("720p", "scale=-2:720", "26")]
        elif mode == "comp_1080p":
            qualities_to_process = [("1080p", "scale=-2:1080", "28")] # Fixed to 28 for heavy compression
        elif mode == "comp_all":
            qualities_to_process = [
                ("360p", "scale=-2:360", "28"),
                ("720p", "scale=-2:720", "26"),
                ("1080p", "scale=-2:1080", "28") # Fixed to 28 for heavy compression
            ]

        for q_label, scale_filter, crf_val in qualities_to_process:
            await status_msg.edit(f"⚙️ **Compressing to {q_label} with Full HD Thumbnail...**")
            output_file = f"output_{user_id}_{q_label}.mp4"
            
            if has_banner:
                filter_complex = f"[0:v]{scale_filter}[v_scaled];[1:v]scale=-1:80:flags=lanczos[banner];[v_scaled][banner]overlay=W-w-20:20[v]"
                command = [
                    FFMPEG_PATH, "-i", downloaded_path, "-i", banner_file,
                    "-filter_complex", filter_complex,
                    "-map", "[v]", "-map", "0:a?",
                    "-c:v", "libx264", "-crf", crf_val, "-preset", "veryfast",
                    "-c:a", "aac", "-b:a", "96k",
                    output_file, "-y"
                ]
            else:
                command = [
                    FFMPEG_PATH, "-i", downloaded_path,
                    "-vf", scale_filter,
                    "-c:v", "libx264", "-crf", crf_val, "-preset", "veryfast",
                    "-c:a", "aac", "-b:a", "96k",
                    output_file, "-y"
                ]
                
            process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await process.wait()
            
            final_output = output_file if os.path.exists(output_file) and os.path.getsize(output_file) > 1024 else downloaded_path
            
            base_name, ext = os.path.splitext(original_name)
            new_filename = f"{base_name}_{q_label}{ext}"
            final_path = os.path.join(os.path.dirname(final_output), new_filename)
            
            if os.path.exists(final_path):
                os.remove(final_path)
            os.rename(final_output, final_path)
            
            thumb_path = banner_file if has_banner else None
            await status_msg.edit(f"📤 **Sending {q_label} compressed video...**")
            
            await client.send_video(
                chat_id=callback_query.message.chat.id,
                video=final_path,
                thumb=thumb_path,
                supports_streaming=True,
                caption=f"📁 `{new_filename}` ({q_label} Compressed)"
            )
            
            if os.path.exists(final_path):
                os.remove(final_path)

        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit(f"❌ Error: `{str(e)}`")
        
    finally:
        if os.path.exists(input_file):
            os.remove(input_file)
        if user_id in USER_VIDEOS:
            del USER_VIDEOS[user_id]

@app.on_callback_query(filters.regex(r"^comp_"))
async def quality_callback_handler(client, callback_query):
    await compress_and_send(client, callback_query, callback_query.data)

# HTTP Server for Railway
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
    if userbot:
        try:
            userbot.start()
            logging.info("✅ Userbot started successfully!")
        except Exception as e:
            logging.warning(f"Userbot start error: {e}")

    try:
        app.run()
    except Exception as e:
        logging.error(f"Bot run error: {e}")
