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

# Aapki generated Session String yahan direct daal di gayi hai
SESSION_STRING = "BQJHHrsAQohDxth8QaB1QzlGPlg2cO1cI-q5Viul5T2qLYszFLakA-2qWY0Bk21lr6dURBASZV3i98pBNIWxlCehYAAckAlk3grALwFyBq-D4cwX2jVOADnnZxcdo0GcAw4pdJdDR1Zdj4SVk8kfOvrEOtzio5fp16gbcFGVMX8tPrXPyNA4TVyg6NbWSayKzMp-pqPsywpR5Ii9OOqf4nGOE9MsZsZgXU3sOkz--DUqOT0HBkVBLFHHnmX1D_RE9PS00My9cfd0cgxszhCB7KWjT9tkpGEEM3UKgY9gksoy3behq2dcrew-negn2aY-s52ynWP1t0Xr6_MbzbcU0Y7zvg9MUAAAAAEuegsXAA"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://nveowfitvoligqecxofr.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_fqZzvMNKkcupSdiGMEtebA_J_UK9z9F")

# 👑 ADMINS CONFIGURATION
ADMINS = [5074717463, 6144546817]

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

# 2️⃣ USERBOT CLIENT INITIALIZE (Safe check if session exists)
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
USER_NEW_FILENAMES = {}
WAITING_FOR_FILENAME = set()
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
            InlineKeyboardButton("🗜️ Video Studio & Rename", callback_data="compress_menu"),
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

# 🤖 CLONE MANAGEMENT MENUS
@app.on_callback_query(filters.regex("clone_menu"))
async def clone_menu(client, callback_query):
    user_id = callback_query.from_user.id
    
    clones_list = []
    try:
        response = supabase.table("clones").select("*").eq("user_id", user_id).execute()
        clones_list = response.data or []
    except Exception:
        pass

    buttons = [
        [InlineKeyboardButton("➕ Add Clone", callback_data="add_clone_prompt")],
    ]
    
    for clone in clones_list:
        bot_name = clone.get("bot_name", "My Clone")
        buttons.append([InlineKeyboardButton(f"🤖 {bot_name}", callback_data=f"manage_clone_{clone.get('id')}")])
        
    buttons.append([InlineKeyboardButton("⬅ Back to Menu", callback_data="back_to_menu")])

    await callback_query.message.edit_text(
        "✨ **Manage Clone's**\n\n"
        "You can now manage and create your very own identical clone bot, mirroring all awesome features, using the given buttons.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query(filters.regex("add_clone_prompt"))
async def add_clone_prompt(client, callback_query):
    user_id = callback_query.from_user.id
    WAITING_FOR_CLONE_TOKEN.add(user_id)
    
    await callback_query.message.edit_text(
        "➕ **Add New Clone Bot**\n\n"
        "Apne bot ka **BotFather Token** yahan chat mein direct bhej do!\n"
        "*(Jaise: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`)*",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back", callback_data="clone_menu")]
        ])
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

@app.on_callback_query(filters.regex("back_to_menu"))
async def back_to_menu(client, callback_query):
    user_id = callback_query.from_user.id
    USER_SETTING_BANNER.discard(user_id)
    WAITING_FOR_FILENAME.discard(user_id)
    WAITING_FOR_CLONE_TOKEN.discard(user_id)
        
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
            InlineKeyboardButton("🤖 Create My Own Clone", callback_data="clone_menu"),
            InlineKeyboardButton("💎 Premium", callback_data="premium")
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

# 🖼 HANDLE PHOTO, VIDEO & TOKEN INPUT
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
async def receive_text_input(client, message):
    user_id = message.from_user.id
    text = message.text.strip()
    if text.startswith("/"):
        return

    if user_id in WAITING_FOR_CLONE_TOKEN:
        WAITING_FOR_CLONE_TOKEN.remove(user_id)
        
        if ":" not in text or len(text) < 20:
            await message.reply_text("❌ Invalid Bot Token! Please try again with a valid BotFather token.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="clone_menu")]]))
            return

        try:
            bot_name = f"Clone_{user_id}"
            supabase.table("clones").insert({
                "user_id": user_id,
                "bot_token": text,
                "bot_name": bot_name
            }).execute()

            await message.reply_text(
                "✅ **Clone Bot Successfully Added!**\n\n"
                f"Aapka clone bot configure ho gaya hai. Ab aap Manage Clone menu se settings control kar sakte hain.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🤖 Go to Clones", callback_data="clone_menu")]])
            )
        except Exception as e:
            await message.reply_text(f"❌ Error saving clone: `{str(e)}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="clone_menu")]]))
        return

    if user_id in WAITING_FOR_FILENAME:
        WAITING_FOR_FILENAME.remove(user_id)
        new_name = text
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
    
    if userbot:
        try:
            userbot.start()
            logging.info("✅ Userbot started successfully!")
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
