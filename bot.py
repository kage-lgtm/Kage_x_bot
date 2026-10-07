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
SESSION_STRING = os.environ.get("SESSION_STRING", "")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

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
USER_COMPRESS_MODE = {}
WAITING_FOR_FILENAME = set()
WAITING_FOR_CLONE_TOKEN = set()
USER_SETTING_BANNER = set()
USER_BANNERS = {}

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
        "🗜 **Video Compressor Studio**\n"
        "👑 **Developer:** @kage_x_edit\n\n"
        "Pehle yahan se apni pasandida mode select karein, ya direct video bhejein:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡ Auto 3-Qualities (360p + 720p + 1080p)", callback_data="qual_multi_auto")],
            [InlineKeyboardButton("🖼 Set Custom Thumbnail", callback_data="set_banner_menu")],
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
            InlineKeyboardButton("🗜 Video Compressor Studio", callback_data="compress_menu"),
            InlineKeyboardButton("🖼 Set Custom Thumbnail", callback_data="set_banner_menu")
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
            safe_file_name = f"downloads/restricted_{message.from_user.id}_{int(time.time())}.mp4"
            os.makedirs("downloads", exist_ok=True)
            
            file_path = await target_msg.download(file_name=safe_file_name, progress=progress_callback)
            
            if not file_path or not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                await progress_msg.edit("❌ Error aagaya bhai: File size equals to 0 B ya download fail ho gaya!")
                return

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

# 🖼 HANDLE PHOTO (Thumbnail Setup)
@app.on_message(filters.photo & filters.private)
async def receive_photo(client, message):
    user_id = message.from_user.id
    if user_id in USER_SETTING_BANNER:
        USER_SETTING_BANNER.remove(user_id)
        banner_path = f"banner_{user_id}.png"
        downloaded_banner = await message.download(file_name=banner_path)
        USER_BANNERS[user_id] = downloaded_banner or banner_path
        
        await message.reply_text(
            "✅ **Thumbnail Saved Successfully!**\n\n"
            "Ab aap jab bhi video compress karenge, ye thumbnail automatically video par lag jayegi.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_menu")]])
        )
    else:
        await message.reply_text("🖼️ Thumbnail set karne ke liye pehle menu se 'Set Custom Thumbnail' par click karein.")

# 🎥 DIRECT VIDEO HANDLER
@app.on_message((filters.video | filters.document) & filters.private)
async def receive_video(client, message):
    user_id = message.from_user.id
    if message.document and not message.document.mime_type.startswith("video"):
        return

    USER_VIDEOS[user_id] = message
    
    quality_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚀 Auto 3-Qualities (360p + 720p + 1080p)", callback_data="qual_multi_auto")
        ],
        [
            InlineKeyboardButton("📱 360p Low", callback_data="qual_360"),
            InlineKeyboardButton("📺 480p SD", callback_data="qual_480")
        ],
        [
            InlineKeyboardButton("🎬 720p HD", callback_data="qual_720"),
            InlineKeyboardButton("💻 1080p Full HD", callback_data="qual_1080")
        ],
        [
            InlineKeyboardButton("🔥 4K Ultra", callback_data="qual_4k"),
            InlineKeyboardButton("✨ Original Size (High Quality HD)", callback_data="qual_orig")
        ]
    ])
    
    await message.reply_text(
        "🗜️ **Video Received Successfully!**\n\n"
        "Quality select karein:",
        reply_markup=quality_keyboard
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
            await message.reply_text("❌ Invalid Bot Token! Please try again.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="clone_menu")]]))
            return

        try:
            bot_name = f"Clone_{user_id}"
            supabase.table("clones").insert({
                "user_id": user_id,
                "bot_token": text,
                "bot_name": bot_name
            }).execute()

            await message.reply_text(
                "✅ **Clone Bot Successfully Added!**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🤖 Go to Clones", callback_data="clone_menu")]])
            )
        except Exception as e:
            await message.reply_text(f"❌ Error: `{str(e)}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="clone_menu")]]))
        return

    if user_id in WAITING_FOR_FILENAME:
        WAITING_FOR_FILENAME.remove(user_id)
        new_name = text
        if not new_name.endswith((".mp4", ".mkv", ".avi", ".mov")):
            new_name += ".mp4"
            
        USER_NEW_FILENAMES[user_id] = new_name
        await start_video_processing(client, message, user_id)

@app.on_callback_query(filters.regex(r"^qual_"))
async def process_quality_choice(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in USER_VIDEOS:
        await callback_query.answer("⚠ Session expired! Dubara video bhejo.", show_alert=True)
        return

    quality_mode = callback_query.data.replace("qual_", "")
    USER_COMPRESS_MODE[user_id] = quality_mode
    
    if quality_mode == "multi_auto":
        await callback_query.message.edit_text("🚀 **Auto Multi-Quality Mode Selected!**\nProcessing 360p, 720p & 1080p versions simultaneously...")
        await start_video_processing(client, callback_query.message, user_id)
        return

    WAITING_FOR_FILENAME.add(user_id)
    
    old_file_name = "video.mp4"
    msg = USER_VIDEOS[user_id]
    if msg.video and msg.video.file_name:
        old_file_name = msg.video.file_name
    elif msg.document and msg.document.file_name:
        old_file_name = msg.document.file_name

    mode_names = {
        "360": "📱 360p Low Quality",
        "480": "📺 480p SD Quality",
        "720": "🎬 720p HD Quality",
        "1080": "💻 1080p Full HD Quality",
        "4k": "🔥 4K Ultra Quality",
        "orig": "✨ Original Resolution (Smart MB Compression)"
    }
    selected_name = mode_names.get(quality_mode, "Custom")

    await callback_query.message.edit_text(
        f"✅ Mode Selected: `{selected_name}`\n\n"
        f"Please Enter New Filename...\n"
        f"Old File Name :- `{old_file_name}`"
    )

# 🚀 FINAL PROCESSING & COMPRESSION FUNCTION
async def start_video_processing(client, message, user_id):
    msg = USER_VIDEOS.get(user_id)
    q_mode = USER_COMPRESS_MODE.get(user_id, "720")
    base_filename = USER_NEW_FILENAMES.get(user_id, "video.mp4")
    
    if not msg:
        await message.reply_text("❌ Video session not found. Please send the video again.")
        return

    status_msg = await message.reply_text("📥 Downloading file...")
    
    input_file = f"input_{user_id}.mp4"
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
                    try:
                        await status_msg.edit(
                            f"📥 Downloading: [{bar}] {pct}%\n"
                            f"📊 {current / (1024*1024):.1f} MB / {total / (1024*1024):.2f} MB"
                        )
                    except Exception:
                        pass

        downloaded_path = await msg.download(file_name=input_file, progress=dl_progress)
        has_banner = os.path.exists(banner_file)
        
        if q_mode == "multi_auto":
            qualities = [
                ("360p", "scale=-2:360", "28"),
                ("720p", "scale=-2:720", "26"),
                ("1080p", "scale=-2:1080", "24")
            ]
            
            name_only, ext = os.path.splitext(base_filename)
            if not ext:
                ext = ".mp4"

            for q_label, s_filter, crf_val in qualities:
                await status_msg.edit(f"⚙ Encoding video into **{q_label}**...")
                out_name = f"output_{user_id}_{q_label}{ext}"
                
                if has_banner:
                    filter_complex = f"[0:v]{s_filter}[v0];[1:v]scale=-1:60[banner];[v0][banner]overlay=W-w-15:15[v]"
                    command = [
                        FFMPEG_PATH, "-i", downloaded_path, "-i", banner_file,
                        "-filter_complex", filter_complex,
                        "-map", "[v]", "-map", "0:a?",
                        "-c:v", "libx264", "-crf", crf_val, "-preset", "medium",
                        "-c:a", "aac", "-b:a", "128k",
                        out_name, "-y"
                    ]
                else:
                    command = [
                        FFMPEG_PATH, "-i", downloaded_path,
                        "-vf", f"{s_filter},format=yuv420p",
                        "-c:v", "libx264", "-crf", crf_val, "-preset", "medium",
                        "-c:a", "aac", "-b:a", "128k",
                        out_name, "-y"
                    ]
                
                proc = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                await proc.wait()
                
                if os.path.exists(out_name):
                    final_caption = f"{name_only}_{q_label}{ext}"
                    await status_msg.edit(f"📤 Uploading **{q_label}** version...")
                    
                    thumb_path = banner_file if has_banner else None
                    if not thumb_path and msg.video and msg.video.thumbs:
                        try:
                            thumb_path = await client.download_media(msg.video.thumbs[0].file_id)
                        except Exception:
                            pass

                    await client.send_video(
                        chat_id=message.chat.id,
                        video=out_name,
                        thumb=thumb_path,
                        supports_streaming=True,
                        caption=final_caption
                    )
                    
                    if thumb_path and thumb_path != banner_file and os.path.exists(thumb_path):
                        os.remove(thumb_path)
                    os.remove(out_name)
            
            await status_msg.edit("✅ **All 3 Qualities successfully generated and sent!**")
            await asyncio.sleep(3)
            await status_msg.delete()

        else:
            await status_msg.edit(f"⚙️ Compressing video...")
            output_file = f"output_{user_id}.mp4"
            
            scale_map = {
                "360": "scale=-2:360",
                "480": "scale=-2:480",
                "720": "scale=-2:720",
                "1080": "scale=-2:1080",
                "4k": "scale=-2:2160",
                "orig": "scale=trunc(iw/2)*2:trunc(ih/2)*2"
            }
            s_filter = scale_map.get(q_mode, "scale=-2:720")
            
            if has_banner:
                filter_complex = f"[0:v]{s_filter}[v0];[1:v]scale=-1:60[banner];[v0][banner]overlay=W-w-15:15[v]"
                command = [
                    FFMPEG_PATH, "-i", downloaded_path, "-i", banner_file,
                    "-filter_complex", filter_complex,
                    "-map", "[v]", "-map", "0:a?",
                    "-c:v", "libx264", "-crf", "26", "-preset", "medium",
                    "-c:a", "aac", "-b:a", "128k",
                    output_file, "-y"
                ]
            else:
                command = [
                    FFMPEG_PATH, "-i", downloaded_path,
                    "-vf", f"{s_filter},format=yuv420p",
                    "-c:v", "libx264", "-crf", "26", "-preset", "medium",
                    "-c:a", "aac", "-b:a", "128k",
                    output_file, "-y"
                ]
            
            process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await process.wait()
            
            final_file = output_file if os.path.exists(output_file) and os.path.getsize(output_file) > 1024 else downloaded_path
            
            renamed_path = os.path.join(os.path.dirname(final_file), base_filename)
            if os.path.exists(renamed_path):
                os.remove(renamed_path)
            os.rename(final_file, renamed_path)
            
            thumb_path = banner_file if has_banner else None
            if not thumb_path and msg.video and msg.video.thumbs:
                try:
                    thumb_path = await client.download_media(msg.video.thumbs[0].file_id)
                except Exception:
                    pass

            await status_msg.edit("📤 Uploading compressed file...")
            await client.send_video(
                chat_id=message.chat.id,
                video=renamed_path,
                thumb=thumb_path,
                supports_streaming=True,
                caption=base_filename
            )
                
            if thumb_path and thumb_path != banner_file and os.path.exists(thumb_path):
                os.remove(thumb_path)
            if os.path.exists(output_file):
                os.remove(output_file)
                
            await status_msg.delete()
        
    except Exception as _err:
        await status_msg.edit(f"❌ Error: `{str(_err)}`")
        
    finally:
        if os.path.exists(input_file):
            os.remove(input_file)
        USER_VIDEOS.pop(user_id, None)
        USER_NEW_FILENAMES.pop(user_id, None)
        USER_COMPRESS_MODE.pop(user_id, None)

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
