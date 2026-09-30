# 🔘 Inline Buttons Callback Handler
@app.on_callback_query()
async def callback_handler(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id

    # Access check yahan bhi
    if ADMINS and user_id not in ADMINS:
        await callback_query.answer("⚠️ Access Denied!", show_alert=True)
        return

    if data == "my_files":
        await callback_query.message.edit_text(
            "📁 **My Files / Hub**\n\n"
            "Yahan aapki saved files aur restricted content ki list dikhegi.\n"
            "Apni file save karne ke liye mujhe direct koi bhi media forward karein.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
            ])
        )
    elif data == "media_downloader":
        await callback_query.message.edit_text(
            "📥 **Universal Media Downloader**\n\n"
            "Kisi bhi platform (YouTube, Instagram, etc.) ki link yahan bhejein aur media download karein.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
            ])
        )
    elif data == "premium":
        await callback_query.message.edit_text(
            "💎 **Premium & Coins Hub**\n\n"
            "Aapka current plan: **Free**\n"
            "Coins balance: 0\n\n"
            "Premium features unlock karne ke liye admin se contact karein.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
            ])
        )
    elif data == "help":
        await callback_query.message.edit_text(
            "⚙️ **Help & Support**\n\n"
            "Kisi bhi problem ke liye developer se sampark karein:\n"
            "👑 **Developer:** @Kage_x_edit",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
            ])
        )
    elif data == "main_menu":
        welcome_text = (
            f"👋 **Hello {callback_query.from_user.first_name}!**\n\n"
            "Welcome to **Kage x Bot** — Your ultimate all-in-one media and file management studio. 🚀\n\n"
            "👑 **Developer / Creator:** Kage (Kage x Edit)\n\n"
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
        await callback_query.message.edit_text(welcome_text, reply_markup=keyboard)
    
    await callback_query.answer()
