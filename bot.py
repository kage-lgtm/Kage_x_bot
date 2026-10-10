import os
import logging
import asyncio
import re
import time
import shutil
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from supabase import create_client, Client as SupabaseClient
import imageio_ffmpeg
import subprocess
import yt_dlp
from datetime import datetime

# Credentials & Supabase Config
API_ID = int(os.environ.get("API_ID", 38215355))
API_HASH = os.environ.get("API_HASH", "3f095c170be8c744b8f3d7f9c75ae544")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8529227386:AAFsqpj5mq4N_fRq1MJ9_hwF-hir7bVGrxw")

SESSION_STRING = "BQJHHrsAQohDxth8QaB1QzlGPlg2cO1cI-q5Viul5T2qLYszFLakA-2qWY0Bk21lr6dURBASZV3i98pBNIWxlCehYAAckAlk3grALwFyBq-D4cwX2jVOADnnZxcdo0GcAw4pdJdDR1Zdj4SVk8kfOvrEOtzio5fp16gbcFGVMX8tPrXPyNA4TVyg6NbWSayKzMp-pqPsywpR5Ii9OOqf4nGOE9MsZsZgXU3sOkz--DUqOT0HBkVBLFHHnmX1D_RE9PS00My9cfd0cgxszhCB7KWjT9tkpGEEM3UKgY9gksoy3behq2dcrew-negn2aY-s52ynWP1t0Xr6_MbzbcU0Y7zvg9MUAAAAAEuegsXAA"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://nveowfitvoligqecxofr.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_fqZzvMNKkcupSdiGMEtebA_J_UK9z9F")

# 👑 MAIN OWNER / ADMIN CONFIGURATION
MAIN_OWNER = 5074717463

# Logging setup
logging.basicConfig(level=logging.INFO)

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

supabase: SupabaseClient = create_client(SUPABASE_URL, SUPABASE_KEY)

# Temporary storage & states
USER_VIDEOS = {}
USER_SETTING_BANNER = set()
USER_BANNERS = {}
WAITING_FOR_DOWNLOAD_LINK = set()
WAITING_FOR_MAIN_EPISODE = set()
WAITING_FOR_DUB_CLIPS = set()
PROCESSING_USERS = set()

def get_user_dir(user_id):
    d = os.path.abspath(f"user_data_{user_id}")
    os.makedirs(d, exist_ok=True)
    return d

def is_authorized(user_id):
    if user_id == MAIN_OWNER:
        return True
    try:
        res = supabase.table("allowed_users").select("*").eq("user_id", user_id).execute()
        return res.data and len(res.data) > 0
    except Exception:
        return False

def log_activity(user_id, username, action_type, details):
    try:
        supabase.table("user_activity_logs").insert({
            "user_id": user_id,
            "username": username or "Unknown",
            "action_type": action_type,
            "details": details,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()
    except Exception as e:
        logging.info(f"Supabase Log Error: {e}")

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    log_activity(user_id, username, "START_BOT", "User started the bot")

    if not is_authorized(user_id):
        await message.reply_text(
            f"👋 **Hello {username}!**\n\n"
            f"Welcome to **Kage x Bot** 🚀\n"
            f"❌ **Access Denied:** Aapke paas is bot ko use karne ki permission nahi hai.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📨 Request Access from Owner", callback_data=f"req_access_{user_id}")]
            ])
        )
        return

    menu_buttons = [
        [
            InlineKeyboardButton("📥 Downloader", callback_data="downloader"),
            InlineKeyboardButton("🗜️ Compressor Studio", callback_data="compress_menu")
        ],
        [
            InlineKeyboardButton("🎬 Dub Sync & Mix Studio", callback_data="dub_studio"),
            InlineKeyboardButton("🖼️ Set Custom Thumbnail", callback_data="set_banner_menu")
        ]
    ]

    if user_id == MAIN_OWNER:
        menu_buttons.append([
            InlineKeyboardButton("📊 View Activity Logs", callback_data="view_logs"),
            InlineKeyboardButton("🔒 Restricted Downloader", callback_data="restricted_dl_info")
        ])

    menu_keyboard = InlineKeyboardMarkup(menu_buttons)
    banner_url = "https://envs.sh/W0K.jpg"
    await message.reply_photo(
        photo=banner_url,
        caption=(
            f"👋 **Hello {username}!**\n\n"
            f"Welcome to **Kage x Bot** (Panda Style Compressor) 🐼🚀\n"
            f"Devloper :- @kage_x_edit\n"
            f"Join channel\nhttps://t.me/+VzwHuVRPyLjOGJl\n\n"
            f"Neeche diye gaye buttons se features explore karein:"
        ),
        reply_markup=menu_keyboard
    )

@app.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message):
    if not is_authorized(message.from_user.id):
        return
    await message.reply_text(
        "🤖 **Bot Commands List:**\n\n"
        "🔹 `/start` - Main Menu\n"
        "🔹 `/compress` - Video Compressor Studio\n"
        "🔹 `/dub` - Dub Sync & Mix Studio\n"
        "🔹 `/setbanner` - Custom Thumbnail Set karein\n"
    )

@app.on_message(filters.command("compress") & filters.private)
async def compress_cmd(client, message):
    if not is_authorized(message.from_user.id):
        return
    await message.reply_text("🗜️ **Panda Style Compressor:** Apni video direct chat mein bhej do!")

@app.on_message(filters.command("setbanner") & filters.private)
async def setbanner_cmd(client, message):
    if not is_authorized(message.from_user.id):
        return
    USER_SETTING_BANNER.add(message.from_user.id)
    await message.reply_text("🖼️ **Thumbnail Setup:** Apni custom thumbnail photo yahan bhej do:")

@app.on_callback_query(filters.regex("set_banner_menu"))
async def set_banner_menu(client, callback_query):
    if not is_authorized(callback_query.from_user.id):
        return
    USER_SETTING_BANNER.add(callback_query.from_user.id)
    await callback_query.message.edit_text(
        "🖼 **Custom Thumbnail Setup**\n\nApni Thumbnail image yahan bhej do:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_menu")]])
    )

@app.on_callback_query(filters.regex("compress_menu"))
async def compress_menu(client, callback_query):
    if not is_authorized(callback_query.from_user.id):
        return
    await callback_query.message.edit_text(
        "🗜 **Panda Style Compressor Studio**\n\nApni video yahan bhej do:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_menu")]])
    )

@app.on_callback_query(filters.regex("dub_studio"))
async def dub_studio_callback(client, callback_query):
    if not is_authorized(callback_query.from_user.id):
        return
    WAITING_FOR_MAIN_EPISODE.add(callback_query.from_user.id)
    await callback_query.message.edit_text(
        "🎬 **Dub Sync & Mix Studio**\n\nSabse pehle apna **Main Episode Video** bhej do:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_menu")]])
    )

@app.on_callback_query(filters.regex("back_to_menu"))
async def back_to_menu(client, callback_query):
    user_id = callback_query.from_user.id
    if not is_authorized(user_id):
        return
    USER_SETTING_BANNER.discard(user_id)
    WAITING_FOR_DOWNLOAD_LINK.discard(user_id)
    WAITING_FOR_MAIN_EPISODE.discard(user_id)
    WAITING_FOR_DUB_CLIPS.discard(user_id)
    PROCESSING_USERS.discard(user_id)
    
    ud = get_user_dir(user_id)
    if os.path.exists(ud):
        shutil.rmtree(ud)
    
    await start_command(client, callback_query.message)

# 🖼️ SEPARATE PHOTO HANDLER ONLY FOR THUMBNAIL
@app.on_message(filters.photo & filters.private)
async def receive_photo(client, message):
    user_id = message.from_user.id
    if not is_authorized(user_id):
        return

    if user_id in USER_SETTING_BANNER:
        USER_SETTING_BANNER.remove(user_id)
        banner_path = f"banner_{user_id}.jpg"
        downloaded_banner = await message.download(file_name=banner_path)
        USER_BANNERS[user_id] = downloaded_banner or banner_path
        
        await message.reply_text(
            "✅ **Thumbnail Saved Successfully!**\nAb compression ke baad video ka thumbnail cover yahi dikhega.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_menu")]])
        )

# 🎬 VIDEO HANDLER
@app.on_message((filters.video | filters.document) & filters.private)
async def receive_video_handler(client, message):
    user_id = message.from_user.id
    if not is_authorized(user_id):
        return

    # Agar user thumbnail set karne ke dauran photo ki jagah video bhej de, toh ignore karein ya handle karein
    if user_id in USER_SETTING_BANNER:
        return

    if message.document:
        fname = (message.document.file_name or "").lower()
        if not fname.endswith(('.mp4', '.mkv', '.mov', '.webm', '.avi', '.m4v')):
            return

    ud = get_user_dir(user_id)

    if user_id in WAITING_FOR_MAIN_EPISODE:
        WAITING_FOR_MAIN_EPISODE.remove(user_id)
        status_msg = await message.reply_text("📥 **Downloading Main Episode...**")
        input_path = os.path.join(ud, "main_ep.mp4")
        try:
            await message.download(file_name=input_path)
            WAITING_FOR_DUB_CLIPS.add(user_id)
            await status_msg.edit(
                "✅ **Main Episode Saved!**\n\nAb apni saari Hindi Dubbed Clips bhejiye:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 Mix & Process Dubbed Episode", callback_data="process_dub_final")],
                    [InlineKeyboardButton("❌ Cancel", callback_data="back_to_menu")]
                ])
            )
        except Exception as e:
            await status_msg.edit(f"❌ Error: `{str(e)}`")
        return

    if user_id in WAITING_FOR_DUB_CLIPS or os.path.exists(os.path.join(ud, "main_ep.mp4")):
        if user_id not in WAITING_FOR_DUB_CLIPS:
            WAITING_FOR_DUB_CLIPS.add(user_id)
        clip_name = f"clip_{int(time.time() * 1000)}_{len(os.listdir(ud))}.mp4"
        await message.download(file_name=os.path.join(ud, clip_name))
        clips_count = len([f for f in os.listdir(ud) if f.startswith("clip_")])
        await message.reply_text(
            f"✅ **Dubbed Clip #{clips_count} Added Successfully!**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🚀 Mix & Process ({clips_count} Clips)", callback_data="process_dub_final")],
                [InlineKeyboardButton("❌ Cancel", callback_data="back_to_menu")]
            ])
        )
        return

    USER_VIDEOS[user_id] = message
    file_name = message.video.file_name if message.video and message.video.file_name else "video.mp4"
    
    quality_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📉 360p (~50MB)", callback_data="comp_360p"),
            InlineKeyboardButton("📊 720p (~150MB)", callback_data="comp_720p")
        ],
        [
            InlineKeyboardButton("📈 1080p (~300MB)", callback_data="comp_1080p"),
            InlineKeyboardButton("🔥 All in 3 Qualities", callback_data="comp_all")
        ]
    ])

    await message.reply_text(
        f"🎬 **Video Received!**\n📁 File: `{file_name}`\n\nSelect compression quality (Panda Style):",
        reply_markup=quality_keyboard
    )

async def compress_and_send(client, callback_query, mode):
    user_id = callback_query.from_user.id
    if not is_authorized(user_id):
        await callback_query.answer("❌ Unauthorized!", show_alert=True)
        return

    if user_id not in USER_VIDEOS:
        await callback_query.answer("⚠ Session expired!", show_alert=True)
        return

    msg = USER_VIDEOS[user_id]
    original_name = msg.video.file_name if msg.video and msg.video.file_name else "video.mp4"
    status_msg = await callback_query.message.edit_text("📥 **Downloading video...**")
    
    input_file = f"input_{user_id}.mp4"
    extracted_thumb = f"thumb_{user_id}.jpg"
    banner_file = USER_BANNERS.get(user_id, f"banner_{user_id}.jpg")
    
    try:
        downloaded_path = await msg.download(file_name=input_file)
        thumb_to_use = banner_file if os.path.exists(banner_file) else None
        if not thumb_to_use:
            try:
                cmd_thumb = [FFMPEG_PATH, "-ss", "00:00:02", "-i", downloaded_path, "-vframes", "1", "-q:v", "2", extracted_thumb, "-y"]
                proc = await asyncio.create_subprocess_exec(*cmd_thumb, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                await proc.wait()
                if os.path.exists(extracted_thumb):
                    thumb_to_use = extracted_thumb
            except Exception:
                pass

        qualities = []
        if mode == "comp_360p":
            qualities = [("360p", "scale=-2:360", "30")]
        elif mode == "comp_720p":
            qualities = [("720p", "scale=-2:720", "26")]
        elif mode == "comp_1080p":
            qualities = [("1080p", "scale=-2:1080", "23")]
        elif mode == "comp_all":
            qualities = [
                ("360p", "scale=-2:360", "30"),
                ("720p", "scale=-2:720", "26"),
                ("1080p", "scale=-2:1080", "23")
            ]

        for q_label, scale_filter, crf_val in qualities:
            await status_msg.edit(f"⚙️ **Panda Compressing to {q_label} (High Clarity, Untouched Audio)...**")
            output_file = f"output_{user_id}_{q_label}.mp4"
            
            command = [
                FFMPEG_PATH, "-i", downloaded_path,
                "-vf", scale_filter,
                "-c:v", "libx264", "-crf", crf_val, "-preset", "slow",
                "-c:a", "copy",
                "-movflags", "+faststart",
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
            
            await status_msg.edit(f"📤 **Sending {q_label} video...**")
            await client.send_video(
                chat_id=callback_query.message.chat.id, video=final_path,
                thumb=thumb_to_use, supports_streaming=True, caption=f"📁 `{new_filename}` ({q_label} Panda Compressed)"
            )
            await asyncio.sleep(1)
            if os.path.exists(final_path):
                os.remove(final_path)

        await status_msg.delete()
    except Exception as e:
        await status_msg.edit(f"❌ Error: `{str(e)}`")
    finally:
        if os.path.exists(input_file):
            os.remove(input_file)
        if os.path.exists(extracted_thumb):
            os.remove(extracted_thumb)
        if user_id in USER_VIDEOS:
            del USER_VIDEOS[user_id]

@app.on_callback_query(filters.regex(r"^comp_"))
async def quality_callback_handler(client, callback_query):
    await compress_and_send(client, callback_query, callback_query.data)

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
