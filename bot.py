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

@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    log_activity(user_id, username, "START_BOT", "User started the bot")

    if not is_authorized(user_id):
        await message.reply_text(
            f"👋 **Hello {username}!**\n\n"
            f"Welcome to **Kage x Bot** 🚀\n"
            f"❌ **Access Denied:** Aapke paas is bot ko use karne ki permission nahi hai.\n\n"
            f"Features use karne ke liye owner se permission lein ya neeche diye gaye button par click karke access request bhejein:",
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

    await message.reply_text(
        f"👋 **Hello {username}!**\n\n"
        f"Welcome to **Kage x Bot** 🚀\n"
        f"👑 **Developer:** @kage_x_edit\n\n"
        f"Neeche diye gaye buttons se features explore karein:",
        reply_markup=menu_keyboard
    )

@app.on_callback_query(filters.regex(r"^req_access_"))
async def request_access_handler(client, callback_query):
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username or callback_query.from_user.first_name
    
    await callback_query.answer("✅ Request main owner ke paas bhej di gayi hai!", show_alert=True)
    await callback_query.message.edit_text("⏳ **Request Sent!** Owner ki approval ka intezaar karein.")
    
    try:
        await client.send_message(
            chat_id=MAIN_OWNER,
            text=f"🔔 **New Access Request!**\n\n"
                 f"👤 User: {username} (`{user_id}`)\n\n"
                 f"Access dene ke liye yeh command bhejein:\n"
                 f"`/grant {user_id}`"
        )
    except Exception:
        pass

@app.on_message(filters.command("grant") & filters.private)
async def grant_access(client, message):
    if message.from_user.id != MAIN_OWNER:
        return
        
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply_text("❌ Sahi format use karein: `/grant <user_id>`")
        return
        
    try:
        target_id = int(parts[1])
        supabase.table("allowed_users").upsert({"user_id": target_id}).execute()
            
        await message.reply_text(f"✅ User `{target_id}` ko successfully access de diya gaya hai!")
        try:
            await client.send_message(target_id, "🎉 **Aapki Access Request Approve ho gayi hai!** Ab aap `/start` bhej kar bot use kar sakte hain.")
        except Exception:
            pass
    except Exception as e:
        await message.reply_text(f"❌ Error: `{str(e)}`")

@app.on_message(filters.command("logs") & filters.private)
async def view_user_logs(client, message):
    if message.from_user.id != MAIN_OWNER:
        return
        
    try:
        res = supabase.table("user_activity_logs").select("*").order("id", desc=True).limit(10).execute()
        logs = res.data or []
        
        if not logs:
            await message.reply_text("📁 Abhi tak koi activity log recorded nahi hai.")
            return
            
        text = "📊 **Recent User Activities (Supabase):**\n\n"
        for log in logs:
            text += f"👤 **User:** `{log.get('user_id')}` ({log.get('username')})\n"
            text += f"⚙️ **Action:** `{log.get('action_type')}`\n"
            text += f"📝 **Details:** {log.get('details')}\n"
            text += f"🕒 **Time:** `{log.get('timestamp')}`\n-----------------------------------\n"
            
        await message.reply_text(text)
    except Exception as e:
        await message.reply_text(f"❌ Error fetching logs: `{str(e)}`")

@app.on_callback_query(filters.regex("view_logs"))
async def view_logs_callback(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id != MAIN_OWNER:
        await callback_query.answer("❌ Ye feature sirf main owner ke liye hai!", show_alert=True)
        return
        
    try:
        res = supabase.table("user_activity_logs").select("*").order("id", desc=True).limit(8).execute()
        logs = res.data or []
        
        if not logs:
            await callback_query.answer("📁 Koi logs nahi hain abhi.", show_alert=True)
            return
            
        text = "📊 **Recent User Activities:**\n\n"
        for log in logs:
            text += f"👤 `{log.get('username')}` | ⚙️ `{log.get('action_type')}`\n📝 {log.get('details')}\n🕒 `{log.get('timestamp')}`\n\n"
            
        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_menu")]])
        )
    except Exception as e:
        await callback_query.answer(f"❌ Error: {str(e)}", show_alert=True)

@app.on_callback_query(filters.regex("restricted_dl_info"))
async def restricted_dl_info(client, callback_query):
    if callback_query.from_user.id != MAIN_OWNER:
        await callback_query.answer("❌ Unauthorized!", show_alert=True)
        return
    await callback_query.message.edit_text(
        "🔒 **Restricted Telegram Downloader**\n\n"
        "Ye feature sirf aapke (Main Owner) ke liye active hai. Aap kisi bhi private/restricted channel ka link direct bhej sakte hain!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_menu")]])
    )

@app.on_callback_query(filters.regex("downloader"))
async def downloader_callback(client, callback_query):
    user_id = callback_query.from_user.id
    if not is_authorized(user_id):
        await callback_query.answer("❌ Aapke paas access nahi hai!", show_alert=True)
        return
        
    WAITING_FOR_DOWNLOAD_LINK.add(user_id)
    log_activity(user_id, callback_query.from_user.username, "OPEN_MENU", "Opened Downloader Menu")
    
    await callback_query.message.edit_text(
        "📥 **Universal Link Downloader**\n\n"
        "Bhai, YouTube ya Instagram ka koi bhi link yahan direct bhej do!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_menu")]])
    )

@app.on_callback_query(filters.regex("compress_menu"))
async def compress_menu(client, callback_query):
    user_id = callback_query.from_user.id
    if not is_authorized(user_id):
        await callback_query.answer("❌ Aapke paas access nahi hai!", show_alert=True)
        return
        
    log_activity(user_id, callback_query.from_user.username, "OPEN_MENU", "Opened Video Compressor Studio")
    
    await callback_query.message.edit_text(
        "🗜 **Video Compressor Studio (High Quality with Thumbnail)**\n"
        "👑 **Developer:** @kage_x_edit\n\n"
        "Bhai, apni video yahan bhej do. Bot high quality ke sath compress karega!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅ Back to Menu", callback_data="back_to_menu")]
        ])
    )

@app.on_callback_query(filters.regex("dub_studio"))
async def dub_studio_callback(client, callback_query):
    user_id = callback_query.from_user.id
    if not is_authorized(user_id):
        await callback_query.answer("❌ Aapke paas access nahi hai!", show_alert=True)
        return
        
    WAITING_FOR_MAIN_EPISODE.add(user_id)
    WAITING_FOR_DUB_CLIPS.discard(user_id)
    PROCESSING_USERS.discard(user_id)
    
    ud = get_user_dir(user_id)
    if os.path.exists(ud):
        shutil.rmtree(ud)
        
    log_activity(user_id, callback_query.from_user.username, "OPEN_MENU", "Opened Dub Sync & Mix Studio")
    
    await callback_query.message.edit_text(
        "🎬 **Dub Sync & Mix Studio**\n"
        "👑 **Developer:** @kage_x_edit\n\n"
        "Bhai, sabse pehle apna **Main Episode Video** alag se bhej do:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_menu")]
        ])
    )

@app.on_callback_query(filters.regex("set_banner_menu"))
async def set_banner_menu(client, callback_query):
    user_id = callback_query.from_user.id
    if not is_authorized(user_id):
        await callback_query.answer("❌ Aapke paas access nahi hai!", show_alert=True)
        return
        
    USER_SETTING_BANNER.add(user_id)
    banner_path = USER_BANNERS.get(user_id, f"banner_{user_id}.png")
    has_banner = os.path.exists(banner_path)
    status_text = "🟢 **Custom thumbnail saved hai!**" if has_banner else "🔴 **Koi thumbnail saved nahi hai.**"
    
    await callback_query.message.edit_text(
        f"🖼 **Custom Thumbnail Setup**\n\n{status_text}\n\nApni Thumbnail image yahan bhej do:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_menu")]])
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
    
    menu_buttons = [
        [
            InlineKeyboardButton("📥 Downloader", callback_data="downloader"),
            InlineKeyboardButton("🗜️ Compressor Studio", callback_data="compress_menu")
        ],
        [
            InlineKeyboardButton("🎬 Dub Sync & Mix Studio", callback_data="dub_studio"),
            InlineKeyboardButton("🖼️ Custom Thumbnail", callback_data="set_banner_menu")
        ]
    ]

    if user_id == MAIN_OWNER:
        menu_buttons.append([
            InlineKeyboardButton("📊 View Activity Logs", callback_data="view_logs"),
            InlineKeyboardButton("🔒 Restricted Downloader", callback_data="restricted_dl_info")
        ])

    menu_keyboard = InlineKeyboardMarkup(menu_buttons)
    
    await callback_query.message.edit_text(
        "👋 **Main Menu**\n👑 **Developer:** @kage_x_edit\n\nNeeche diye gaye buttons se features explore karein:",
        reply_markup=menu_keyboard
    )

@app.on_message(filters.regex(r"https?://") & filters.private)
async def universal_link_handler(client, message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    if not is_authorized(user_id):
        await message.reply_text("❌ Aapke paas is bot ko use karne ki permission nahi hai!")
        return

    link = message.text.strip()
    log_activity(user_id, username, "DOWNLOAD_LINK", f"Link: {link}")

    if "t.me/" in link:
        if user_id != MAIN_OWNER:
            await message.reply_text("❌ Restricted / Saved Telegram content download karne ka access sirf Main Owner ke paas hai!")
            return

        if not userbot:
            await message.reply_text("❌ Telegram downloader ke liye `SESSION_STRING` configured nahi hai!")
            return

        match = re.search(r"t\.me/(?:c/)?([a-zA-Z0-9_]+)/(\d+)", link)
        if not match:
            await message.reply_text("❌ Invalid Telegram link format!")
            return
            
        chat_identifier = match.group(1)
        msg_id = int(match.group(2))
        chat_id = int("-100" + chat_identifier) if chat_identifier.isdigit() else "@" + chat_identifier
            
        progress_msg = await message.reply_text("📥 **Fetching Telegram restricted content...**")

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
                
                banner_file = USER_BANNERS.get(user_id, f"banner_{user_id}.png")
                thumb_path = banner_file if os.path.exists(banner_file) else None

                if target_msg.video:
                    await client.send_video(
                        chat_id=message.chat.id, video=file_path, thumb=thumb_path,
                        duration=target_msg.video.duration, width=target_msg.video.width,
                        height=target_msg.video.height, supports_streaming=True, caption=target_msg.caption or ""
                    )
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
            await progress_msg.edit(f"❌ Error: `{str(e)}`")
            
    else:
        progress_msg = await message.reply_text("📥 **Downloading media from link (Insta/YT)...**")
        ydl_opts = {
            'outtmpl': f'downloaded_{message.from_user.id}.%(ext)s',
            'max_filesize': 500 * 1024 * 1024,
            'noplaylist': True,
        }
        
        downloaded_files = []
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=True)
                if 'entries' in info:
                    for entry in info['entries']:
                        filename = ydl.prepare_filename(entry)
                        if os.path.exists(filename):
                            downloaded_files.append(filename)
                else:
                    filename = ydl.prepare_filename(info)
                    if os.path.exists(filename):
                        downloaded_files.append(filename)

            if downloaded_files:
                await progress_msg.edit("📤 **Uploading media file(s)...**")
                banner_file = USER_BANNERS.get(user_id, f"banner_{user_id}.png")
                thumb_path = banner_file if os.path.exists(banner_file) else None

                for file_path in downloaded_files:
                    if file_path.endswith(('.mp4', '.mkv', '.webm', '.mov')):
                        await client.send_video(chat_id=message.chat.id, video=file_path, thumb=thumb_path, supports_streaming=True)
                    elif file_path.endswith(('.jpg', '.jpeg', '.png', '.webp', '.jfif')):
                        await client.send_photo(chat_id=message.chat.id, photo=file_path)
                    else:
                        await client.send_document(chat_id=message.chat.id, document=file_path)
                    
                    if os.path.exists(file_path):
                        os.remove(file_path)
                await progress_msg.delete()
            else:
                await progress_msg.edit("❌ Is link par koi download karne layak media nahi mila!")
        except Exception as e:
            await progress_msg.edit(f"❌ Download Error: `{str(e)}`")

@app.on_message(filters.photo & filters.private)
async def receive_photo(client, message):
    user_id = message.from_user.id
    if not is_authorized(user_id):
        return

    if user_id in USER_SETTING_BANNER:
        USER_SETTING_BANNER.remove(user_id)
        banner_path = f"banner_{user_id}.png"
        downloaded_banner = await message.download(file_name=banner_path)
        USER_BANNERS[user_id] = downloaded_banner or banner_path
        
        log_activity(user_id, message.from_user.username, "SET_THUMBNAIL", "Saved Custom Thumbnail")
        await message.reply_text(
            "✅ **Thumbnail Saved Successfully!**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_menu")]])
        )

@app.on_message((filters.video | filters.document) & filters.private)
async def receive_video_handler(client, message):
    user_id = message.from_user.id
    if not is_authorized(user_id):
        await message.reply_text("❌ Aapke paas is bot ko use karne ki permission nahi hai!")
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
        clip_path = os.path.join(ud, clip_name)
        await message.download(file_name=clip_path)
        
        clips_count = len([f for f in os.listdir(ud) if f.startswith("clip_")])
        
        await message.reply_text(
            f"✅ **Dubbed Clip #{clips_count} Added Successfully!**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🚀 Mix & Process Dubbed Episode ({clips_count} Clips)", callback_data="process_dub_final")],
                [InlineKeyboardButton("❌ Cancel", callback_data="back_to_menu")]
            ])
        )
        return

    USER_VIDEOS[user_id] = message
    file_name = message.video.file_name if message.video and message.video.file_name else (message.document.file_name if message.document else "video.mp4")
    
    log_activity(user_id, message.from_user.username, "UPLOAD_VIDEO", f"Video: {file_name}")

    quality_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📉 360p (High Clarity)", callback_data="comp_360p"),
            InlineKeyboardButton("📊 720p (High Clarity)", callback_data="comp_720p")
        ],
        [
            InlineKeyboardButton("📈 1080p (HD High Clarity)", callback_data="comp_1080p"),
            InlineKeyboardButton("🔥 All in 3 Qualities (360+720+1080)", callback_data="comp_all")
        ]
    ])

    await message.reply_text(
        f"🎬 **Video Received for Compression!**\n📁 File: `{file_name}`\n\nSelect compression quality:",
        reply_markup=quality_keyboard
    )

@app.on_callback_query(filters.regex("process_dub_final"))
async def process_dub_final_callback(client, callback_query):
    user_id = callback_query.from_user.id

    if user_id in PROCESSING_USERS:
        await callback_query.answer("⏳ Processing pehle se chal rahi hai!", show_alert=True)
        return

    ud = get_user_dir(user_id)
    main_ep = os.path.join(ud, "main_ep.mp4")
    
    PROCESSING_USERS.add(user_id)
    await callback_query.answer("🚀 Processing start ho gayi hai...")

    try:
        await callback_query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    clips = sorted([os.path.join(ud, f) for f in os.listdir(ud) if f.startswith("clip_")])

    status_msg = await callback_query.message.edit_text(f"⚙️ **Processing Dub Mix:** Merging {len(clips)} clips...")
    output_final = os.path.abspath(f"final_synced_episode_{user_id}.mp4")
    
    try:
        if not clips and os.path.exists(main_ep):
            shutil.copy(main_ep, output_final)
        elif clips:
            inputs = []
            filter_complex = ""
            valid_clips = 0
            
            for clip in clips:
                if os.path.exists(clip):
                    inputs.extend(["-i", clip])
                    filter_complex += f"[{valid_clips}:v][{valid_clips}:a]"
                    valid_clips += 1
            
            if valid_clips > 0:
                filter_complex += f"concat=n={valid_clips}:v=1:a=1[outv][outa]"
                
                command = [
                    FFMPEG_PATH, *inputs,
                    "-filter_complex", filter_complex,
                    "-map", "[outv]", "-map", "[outa]",
                    "-c:v", "libx264", "-crf", "20", "-preset", "medium",
                    "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart",
                    output_final, "-y"
                ]
                
                process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                await process.wait()
            
            if not os.path.exists(output_final) or os.path.getsize(output_final) < 1024:
                if os.path.exists(main_ep):
                    shutil.copy(main_ep, output_final)
        
        banner_file = USER_BANNERS.get(user_id, f"banner_{user_id}.png")
        thumb_path = banner_file if os.path.exists(banner_file) else None

        await status_msg.edit("📤 **Uploading Final Episode...**")
        await client.send_video(
            chat_id=callback_query.message.chat.id,
            video=output_final,
            thumb=thumb_path,
            supports_streaming=True,
            caption="🎬 **Final Hindi Dubbed Anime Episode**"
        )
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit(f"❌ Error: `{str(e)}`")
    finally:
        if os.path.exists(ud):
            shutil.rmtree(ud)
        if output_final and os.path.exists(output_final):
            os.remove(output_final)
            
        PROCESSING_USERS.discard(user_id)
        WAITING_FOR_DUB_CLIPS.discard(user_id)

async def compress_and_send(client, callback_query, mode):
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username or callback_query.from_user.first_name
    
    if not is_authorized(user_id):
        await callback_query.answer("❌ Unauthorized!", show_alert=True)
        return

    if user_id not in USER_VIDEOS:
        await callback_query.answer("⚠ Session expired!", show_alert=True)
        return

    msg = USER_VIDEOS[user_id]
    original_name = "video.mp4"
    if msg.video and msg.video.file_name:
        original_name = msg.video.file_name
    elif msg.document and msg.document.file_name:
        original_name = msg.document.file_name

    log_activity(user_id, username, "COMPRESS", f"File: {original_name} | Mode: {mode}")

    status_msg = await callback_query.message.edit_text("📥 **Downloading video...**")
    
    input_file = f"input_{user_id}.mp4"
    extracted_thumb = f"thumb_{user_id}.jpg"
    banner_file = USER_BANNERS.get(user_id, f"banner_{user_id}.png")
    
    try:
        downloaded_path = await msg.download(file_name=input_file)
        
        thumb_to_use = None
        if os.path.exists(banner_file):
            thumb_to_use = banner_file
        else:
            try:
                cmd_thumb = [
                    FFMPEG_PATH, "-ss", "00:00:01", "-i", downloaded_path,
                    "-vframes", "1", "-q:v", "2", extracted_thumb, "-y"
                ]
                proc_thumb = await asyncio.create_subprocess_exec(*cmd_thumb, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                await proc_thumb.wait()
                if os.path.exists(extracted_thumb):
                    thumb_to_use = extracted_thumb
            except Exception:
                pass

        qualities_to_process = []
        if mode == "comp_360p":
            qualities_to_process = [("360p", "scale=-2:360", "20")]
        elif mode == "comp_720p":
            qualities_to_process = [("720p", "scale=-2:720", "20")]
        elif mode == "comp_1080p":
            qualities_to_process = [("1080p", "scale=-2:1080", "20")]
        elif mode == "comp_all":
            qualities_to_process = [
                ("360p", "scale=-2:360", "20"),
                ("720p", "scale=-2:720", "20"),
                ("1080p", "scale=-2:1080", "20")
            ]

        for q_label, scale_filter, crf_val in qualities_to_process:
            await status_msg.edit(f"⚙️ **Compressing to {q_label} (High Clarity)...**")
            output_file = f"output_{user_id}_{q_label}.mp4"
            
            command = [
                FFMPEG_PATH, "-i", downloaded_path,
                "-vf", scale_filter,
                "-c:v", "libx264", "-crf", crf_val, "-preset", "medium",
                "-c:a", "aac", "-b:a", "128k",
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
                chat_id=callback_query.message.chat.id,
                video=final_path,
                thumb=thumb_to_use,
                supports_streaming=True,
                caption=f"📁 `{new_filename}` ({q_label} High Clarity)"
            )
            
            await asyncio.sleep(1)
            
            if os.path.exists(final_path):
                os.remove(final_path)

        await status_msg.delete()
        
    except Exception as e:
        log_activity(user_id, username, "ERROR_COMPRESS", str(e))
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
