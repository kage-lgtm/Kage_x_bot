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
    match = re.search(r"t\.me/(?:c
