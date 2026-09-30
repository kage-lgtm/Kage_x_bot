import os
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from supabase import create_client, Client as SupabaseClient

# Credentials & Supabase Config
API_ID = 38215355
API_HASH = "3f095c170be8c744b8f3d7f9c75ae544"
BOT_TOKEN = "8529227386:AAFsqpj5mq4N_fRq1MJ9_hwF-hir7bVGrxw"

SUPABASE_URL = "https://zjfuvwvzjpwmytmvywib.supabase.co"
SUPABASE_KEY = "sb_publishable_r8cPTMZLPK18QagNbIUz-w_uuOruHEQ"

# 👑 ADMINS CONFIGURATION (Teri aur dost ki ID)
ADMINS = [5074717463, 6144546817]

# Logging setup
logging.basicConfig(level=logging.INFO)

# Pyrogram Bot Client Initialize karo
app = Client(
    "Kage_x_Bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Supabase Database Client Initialize karo
supabase: SupabaseClient = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    # 🔒 ACCESS CONTROL CHECK
    if ADMINS and user_id not in ADMINS:
        await message.reply_text(
            "⚠️ **Access Denied!**\n\n"
            "Yeh ek private bot hai. Aapke paas isko use karne ki permission nahi hai.\n"
            "Access ke liye developer se contact karein: **@Kage_x_edit**"
        )
        return

    # Database mein user save karne ka logic
    try:
        existing_user = supabase.table("users").select("user_id").eq("user_id", user_id).execute()
        if not existing_user.data:
            supabase.table("users").insert({
                "user_id": user_id,
                "username": username,
                "coins": 0,
                "is_premium": False
            }).execute()
    except Exception as e:
        logging.error(f"Database Error: {e}")

    # Welcome Message with Developer / Brand Details
    welcome_text = (
        f"👋 **Hello {username}!\n\n**"
        "Welcome to **Kage x Bot** — Your ultimate all-in-one media and file management studio. 🚀\n\n"
        "👑 **Developer / Creator:** Kage (Kage x Edit)\n"
        "🎬 **Studio:** ZK Dubbing Studio\n\n"
        "✨ **What I can do:**\n"
        "📁 File Store & Restricted Content Saving\n"
        "📥 Universal Media Downloader (YouTube, Insta, etc.)\n"
        "🌐 Subtitle & Translation Tools\n"
        "⚡ Fast & Free Processing!\n\n"
        "Neeche diye gaye buttons se features explore karein:"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📁 My Files / Hub", callback_data="my_files"),
         InlineKeyboardButton("📥 Downloader", callback_data="media_downloader")],
        [InlineKeyboardButton("💎 Premium & Coins", callback_data="premium"),
         InlineKeyboardButton("⚙️ Help & Support", callback_data="help")]
    ])

    await message.reply_text(welcome_text, reply_markup=keyboard)

# Bot Run karne ke liye
if __name__ == "__main__":
    print("🤖 Kage x Bot is starting...")
    app.run()
