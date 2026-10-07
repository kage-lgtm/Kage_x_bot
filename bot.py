import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- CREDENTIALS & CONFIGURATION ---
API_ID = 38215355
API_HASH = "3f095c170be8c744b8f3d7f9c75ae544"
BOT_TOKEN = "8529227386:AAFsqpj5mq4N_fRq1MJ9_hwF-hir7bVGrxw"

# Aapki generated Session String yahan daal di gayi hai
SESSION_STRING = "BQJHHrsAQohDxth8QaB1QzlGPlg2cO1cI-q5Viul5T2qLYszFLakA-2qWY0Bk21lr6dURBASZV3i98pBNIWxlCehYAAckAlk3grALwFyBq-D4cwX2jVOADnnZxcdo0GcAw4pdJdDR1Zdj4SVk8kfOvrEOtzio5fp16gbcFGVMX8tPrXPyNA4TVyg6NbWSayKzMp-pqPsywpR5Ii9OOqf4nGOE9MsZsZgXU3sOkz--DUqOT0HBkVBLFHHnmX1D_RE9PS00My9cfd0cgxszhCB7KWjT9tkpGEEM3UKgY9gksoy3behq2dcrew-negn2aY-s52ynWP1t0Xr6_MbzbcU0Y7zvg9MUAAAAAEuegsXAA"

# Supabase Credentials
SUPABASE_URL = "https://nveowfitvoligqecxofr.supabase.co"
SUPABASE_KEY = "sb_publishable_fqZzvMNKkcupSdiGMEtebA_J_UK9z9F"

# --- CLIENT INITIALIZATION ---
# Main Bot Client
app = Client(
    "kage_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Userbot Client (Restricted content downloader ke liye)
userbot = None
if SESSION_STRING:
    try:
        userbot = Client(
            "kage_userbot",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=SESSION_STRING
        )
    except Exception as e:
        print(f"Userbot initialization warning: {e}")

# --- START COMMAND & WELCOME MESSAGE ---
@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    try:
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
    except Exception as e:
        print(f"Start command error: {e}")

# --- MAIN RUNNER ---
if __name__ == "__main__":
    print("🤖 Starting Kage x Bot & Userbot...")
    if userbot:
        try:
            userbot.start()
            print("✅ Userbot started successfully with Session String!")
        except Exception as e:
            print(f"⚠️ Userbot start failed: {e}")
    
    app.run()
