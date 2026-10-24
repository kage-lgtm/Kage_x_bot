import os
import logging
import asyncio
import time
import shutil
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from supabase import create_client, Client as SupabaseClient
import imageio_ffmpeg
import yt_dlp
from datetime import datetime

# Credentials & Supabase Config
API_ID = int(os.environ.get("API_ID", 38215355))
API_HASH = os.environ.get("API_HASH", "3f095c170be8c744b8f3d7f9c75ae544")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8529227386:AAFsqpj5mq4N_fRq1MJ9_hwF-hir7bVGrxw")

SESSION_STRING = "BQJHHrsAQohDxth8QaB1QzlGPlg2cO1cI-q5Viul5T2qLYszFLakA-2qWY0Bk21lr6dURBASZV3i98pBNIWxlCehYAAckAlk3grALwFyBq-D4cwX2jVOADnnZxcdo0GcAw4pdJdDR1Zdj4SVk8kfOvrEOtzio5fp16gbcFGVMX8tPrXPyNA4TVyg6NbWSayKzMp-pqPsywpR5Ii9OOqf4nGOE9MsZsZgXU3sOkz--DUqOT0HBkVBLFHHnmX1D_RE9PS00My9cfd0cgxszhCB7KWjT9tkpGEEM3UKgY9gksoy3behq2dcrew-negn2aY-s52ynWP1t0Xr6_MbzbcU0Y7zvg9MUAAAAAEuegsXAA"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://nveowfitvoligqecxofr.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_fqZzvMNKkcupSdiGMEtebA_J_UK9z9F")

# 👑 MAIN OWNER ID
MAIN_OWNER = 5074717463

logging.basicConfig(level=logging.INFO)
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

app = Client(
    "Kage_x_Bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

userbot = None
if SESSION_STRING and len(SESSION_STRING) > 20:
    userbot = Client(
        "Kage_Userbot",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=SESSION_STRING
    )

supabase: SupabaseClient = create_client(SUPABASE_URL, SUPABASE_KEY)

USER_SETTING_BANNER = set()
USER_BANNERS = {}
USER_VIDEOS = {}
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

async def get_video_metadata(file_path):
    ffprobe_path = FFMPEG_PATH.replace("ffmpeg", "ffprobe")
    if not os.path.exists(ffprobe_path):
        ffprobe_path = "ffprobe"
    cmd = [
        ffprobe_path, "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration",
        "-of", "json", file_path
    ]
    try:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await proc.communicate()
        data = json.loads(stdout.decode())
        stream = data.get("streams", [{}])[0]
        width = int(stream.get("width", 1280))
        height = int(stream.get("height", 720))
        duration = int(float(stream.get("duration", 0)))
        return width, height, duration
    except Exception:
        return 1280, 720, 0

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
            InlineKeyboardButton("📊 View Activity Logs", callback_data="view_logs")
        ])

    menu_keyboard = InlineKeyboardMarkup(menu_buttons)
    banner_url = "https://envs.sh/W0K.jpg"
    await message.reply_photo(
        photo=banner_url,
        caption=(
            f"👋 **Hello {username}!**\n\n"
            f"Welcome to **Kage x Bot** (Multi-Quality Compressor & HD Cover) 🐼🚀\n"
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
    help_msg = (
        "🤖 **Bot Commands List:**\n\n"
        "🔹 `/start` - Main Menu\n"
        "🔹 `/compress` - Video Compressor Studio\n"
        "🔹 `/dub` - Dub Sync & Mix Studio\n"
        "🔹 `/setbanner` - Custom Thumbnail Set karein\n"
    )
    if message.from_user.id == MAIN_OWNER:
        help_msg += "\n👑 **Owner Commands:**\n🔹 `/grant <user_id>` - Access dein\n🔹 `/revoke <user_id>` - Access remove karein"
    await message.reply_text(help_msg)

@app.on_message(filters.command("grant") & filters.private)
async def grant_access(client, message):
    if message.from_user.id != MAIN_OWNER:
        await message.reply_text("❌ Yeh command sirf Owner ke liye hai!")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply_text("❌ Sahi format: `/grant <user_id>`")
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

@app.on_message(filters.command("revoke") & filters.private)
async def revoke_access(client, message):
    if message.from_user.id != MAIN_OWNER:
        await message.reply_text("❌ Yeh command sirf Owner ke liye hai!")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply_text("❌ Sahi format: `/revoke <user_id>`")
        return
    try:
        target_id = int(parts[1])
        supabase.table("allowed_users").delete().eq("user_id", target_id).execute()
        await message.reply_text(f"✅ User `{target_id}` ka access remove kar diya gaya hai!")
        try:
            await client.send_message(target_id, "❌ **Aapka access hata diya gaya hai!**")
        except Exception:
            pass
    except Exception as e:
        await message.reply_text(f"❌ Error: `{str(e)}`")

@app.on_callback_query(filters.regex(r"^req_access_"))
async def request_access_handler(client, callback_query):
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username or callback_query.from_user.first_name
    await callback_query.answer("✅ Request main owner ke paas bhej di gayi hai!", show_alert=True)
    await callback_query.message.edit_text("⏳ **Request Sent!** Owner ki approval ka intezaar karein.")
    try:
        await client.send_message(
            chat_id=MAIN_OWNER,
            text=f"🔔 **New Access Request!**\n\n👤 User: {username} (`{user_id}`)\nGrant command:\n`/grant {user_id}`"
        )
    except Exception:
        pass

@app.on_callback_query(filters.regex("view_logs"))
async def view_logs_callback(client, callback_query):
    if callback_query.from_user.id != MAIN_OWNER:
        await callback_query.answer("❌ Unauthorized!", show_alert=True)
        return
    try:
        res = supabase.table("user_activity_logs").select("*").order("id", desc=True).limit(8).execute()
        logs = res.data or []
        text = "📊 **Recent User Activities:**\n\n"
        for log in logs:
            text += f"👤 `{log.get('username')}` | ⚙️ `{log.get('action_type')}`\n🕒 `{log.get('timestamp')}`\n\n"
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_menu")]]))
    except Exception as e:
        await callback_query.answer(f"❌ Error: {str(e)}", show_alert=True)

@app.on_callback_query(filters.regex("downloader"))
async def downloader_callback(client, callback_query):
    if not is_authorized(callback_query.from_user.id):
        return
    WAITING_FOR_DOWNLOAD_LINK.add(callback_query.from_user.id)
    await callback_query.message.edit_text(
        "📥 **Universal Link Downloader**\n\nYouTube ya Instagram ka link yahan bhej do:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_menu")]])
    )

@app.on_callback_query(filters.regex("compress_menu"))
async def compress_menu(client, callback_query):
    if not is_authorized(callback_query.from_user.id):
        return
    await callback_query.message.edit_text(
        "🗜 **Compressor Studio**\n\nApni video bhej do (Quality options milenge):",
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

@app.on_callback_query(filters.regex("set_banner_menu"))
async def set_banner_menu(client, callback_query):
    if not is_authorized(callback_query.from_user.id):
        return
    USER_SETTING_BANNER.add(callback_query.from_user.id)
    await callback_query.message.edit_text(
        "🖼 **Custom Thumbnail Setup**\n\nApni Custom Thumbnail image (Photo ya Document) yahan bhej do:",
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
    if user_id in USER_VIDEOS:
        del USER_VIDEOS[user_id]
    
    ud = get_user_dir(user_id)
    if os.path.exists(ud):
        shutil.rmtree(ud)
    
    await start_command(client, callback_query.message)

@app.on_message((filters.photo | filters.document) & filters.private)
async def receive_banner_media(client, message):
    user_id = message.from_user.id
    if not is_authorized(user_id):
        return

    if user_id in USER_SETTING_BANNER:
        USER_SETTING_BANNER.remove(user_id)
        raw_banner_path = os.path.abspath(f"raw_banner_{user_id}.jpg")
        banner_path = os.path.abspath(f"banner_{user_id}.jpg")
        
        try:
            if message.document:
                await message.download(file_name=raw_banner_path)
            else:
                await client.download_media(message.photo.file_id, file_name=raw_banner_path)
            
            cmd_conv = [
                FFMPEG_PATH, "-i", raw_banner_path,
                "-vf", "scale=640:640:force_original_aspect_ratio=decrease",
                "-pix_fmt", "yuvj420p",
                "-q:v", "1",
                banner_path, "-y"
            ]
            proc = await asyncio.create_subprocess_exec(*cmd_conv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await proc.wait()

            if os.path.exists(banner_path) and os.path.getsize(banner_path) > 0:
                USER_BANNERS[user_id] = banner_path
            else:
                shutil.copy(raw_banner_path, banner_path)
                USER_BANNERS[user_id] = banner_path
            
            await message.reply_text(
                "✅ **HD Custom Cover Saved Successfully!**\nAb aap jab bhi video bhejenge, thumbnail bilkul high quality mein turant dikhegi.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_menu")]])
            )
            return
        except Exception as e:
            await message.reply_text(f"❌ Thumbnail saving error: `{str(e)}`")
            return

    if message.document:
        fname = (message.document.file_name or "").lower()
        if not fname.endswith(('.mp4', '.mkv', '.mov', '.webm', '.avi', '.m4v')):
            return

    await handle_incoming_video(client, message, user_id)

@app.on_message(filters.video & filters.private)
async def receive_video_direct(client, message):
    user_id = message.from_user.id
    if not is_authorized(user_id):
        await message.reply_text("❌ Aapke paas access nahi hai!")
        return
    if user_id in USER_SETTING_BANNER:
        return
    await handle_incoming_video(client, message, user_id)

async def handle_incoming_video(client, message, user_id):
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

    # Store video message for quality selection menu
    USER_VIDEOS[user_id] = message
    file_name = message.video.file_name if message.video and message.video.file_name else (message.document.file_name if message.document else "video.mp4")

    quality_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📉 480p (High Compression)", callback_data="comp_480p"),
            InlineKeyboardButton("📊 720p (Balanced HD)", callback_data="comp_720p")
        ],
        [
            InlineKeyboardButton("📈 1080p (FHD Quality)", callback_data="comp_1080p"),
            InlineKeyboardButton("🔥 Zero Compression (Sirf HD Thumbnail)", callback_data="comp_zerocompress")
        ]
    ])

    await message.reply_text(
        f"🎬 **Video Received!**\n📁 File: `{file_name}`\n\nApni pasand ki quality select karein:",
        reply_markup=quality_keyboard
    )

@app.on_callback_query(filters.regex(r"^comp_"))
async def quality_callback_handler(client, callback_query):
    user_id = callback_query.from_user.id
    if not is_authorized(user_id):
        await callback_query.answer("❌ Unauthorized!", show_alert=True)
        return

    if user_id not in USER_VIDEOS:
        await callback_query.answer("⚠ Session expired! Dobara video bhejein.", show_alert=True)
        return

    mode = callback_query.data
    msg = USER_VIDEOS[user_id]
    original_name = msg.video.file_name if msg.video and msg.video.file_name else (msg.document.file_name if msg.document else "video.mp4")
    status_msg = await callback_query.message.edit_text("📥 **Downloading video...**")
    
    ud = get_user_dir(user_id)
    input_file = os.path.join(ud, f"input_{user_id}{os.path.splitext(original_name)[1]}")
    resized_thumb = os.path.join(ud, f"thumb_{user_id}.jpg")
    banner_file = USER_BANNERS.get(user_id, f"banner_{user_id}.jpg")
    
    try:
        downloaded_path = await message_download_path = await msg.download(file_name=input_file)
        thumb_to_use = None
        if banner_file and os.path.exists(banner_file):
            cmd_thumb = [
                FFMPEG_PATH, "-i", banner_file,
                "-vf", "scale=640:640:force_original_aspect_ratio=decrease",
                "-pix_fmt", "yuvj420p",
                "-q:v", "1",
                resized_thumb, "-y"
            ]
            proc_t = await asyncio.create_subprocess_exec(*cmd_thumb, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await proc_t.wait()
            if os.path.exists(resized_thumb) and os.path.getsize(resized_thumb) > 0:
                thumb_to_use = resized_thumb

        output_file = os.path.join(ud, f"output_{user_id}.mp4")

        if mode == "comp_zerocompress":
            status_msg = await status_msg.edit("⚡ **Instant Remuxing with HD Cover...**")
            cmd = [
                FFMPEG_PATH, "-i", downloaded_path,
                "-c", "copy",
                "-movflags", "+faststart",
                output_file, "-y"
            ]
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await proc.wait()
            final_video = output_file if os.path.exists(output_file) and os.path.getsize(output_file) > 1024 else downloaded_path
            q_label = "Original"
        else:
            # Resolution & Compression settings
            if mode == "comp_480p":
                scale_filter = "scale=-2:480"
                crf_val = "28"
                q_label = "480p"
            elif mode == "comp_720p":
                scale_filter = "scale=-2:720"
                crf_val = "24"
                q_label = "720p"
            else: # comp_1080p
                scale_filter = "scale=-2:1080"
                crf_val = "21"
                q_label = "1080p"

            status_msg = await status_msg.edit(f"🗜 **Compressing to {q_label} (Panda Style) & attaching HD Cover...**")
            cmd = [
                FFMPEG_PATH, "-i", downloaded_path,
                "-vf", scale_filter,
                "-c:v", "libx264", "-crf", crf_val, "-preset", "veryfast",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",
                output_file, "-y"
            ]
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await proc.wait()
            final_video = output_file if os.path.exists(output_file) and os.path.getsize(output_file) > 1024 else downloaded_path

        width, height, duration = await get_video_metadata(final_video)
        base_name, ext = os.path.splitext(original_name)
        new_filename = f"{base_name}_{q_label}.mp4"

        await status_msg.edit(f"📤 **Uploading {q_label} video with HD Cover...**")
        await client.send_video(
            chat_id=callback_query.message.chat.id,
            video=final_video,
            thumb=thumb_to_use,
            width=width,
            height=height,
            duration=duration,
            supports_streaming=True,
            caption=f"📁 `{new_filename}` ({q_label} Compressed & HD Cover Attached)"
        )
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit(f"❌ Error: `{str(e)}`")
    finally:
        if os.path.exists(ud):
            shutil.rmtree(ud)
        if user_id in USER_VIDEOS:
            del USER_VIDEOS[user_id]

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
                    FFMPEG_PATH, *inputs, "-filter_complex", filter_complex,
                    "-map", "[outv]", "-map", "[outa]",
                    "-c:v", "libx264", "-crf", "22", "-preset", "medium",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart",
                    output_final, "-y"
                ]
                process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                await process.wait()
            if not os.path.exists(output_final) or os.path.getsize(output_final) < 1024:
                if os.path.exists(main_ep):
                    shutil.copy(main_ep, output_final)
        
        banner_file = USER_BANNERS.get(user_id, f"banner_{user_id}.jpg")
        thumb_path = None
        if banner_file and os.path.exists(banner_file):
            resized_dub_thumb = os.path.join(ud, f"dub_thumb_{user_id}.jpg")
            cmd_dub_thumb = [
                FFMPEG_PATH, "-i", banner_file,
                "-vf", "scale=640:640:force_original_aspect_ratio=decrease",
                "-pix_fmt", "yuvj420p",
                "-q:v", "1",
                resized_dub_thumb, "-y"
            ]
            proc = await asyncio.create_subprocess_exec(*cmd_dub_thumb, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await proc.wait()
            if os.path.exists(resized_dub_thumb):
                thumb_path = resized_dub_thumb

        width, height, duration = await get_video_metadata(output_final)

        await status_msg.edit("📤 **Uploading Final Dubbed Episode...**")
        await client.send_video(
            chat_id=callback_query.message.chat.id, video=output_final,
            thumb=thumb_path, width=width, height=height, duration=duration, supports_streaming=True, caption="🎬 **Final Hindi Dubbed Anime Episode**"
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
