import logging
import random
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
    ConversationHandler
)
from database import Database

# --- SOZLAMALAR ---
BOT_TOKEN = "8582560566:AAGd87OTCBmoSH0WQPZ2ObgP44SXwQR8mVc"
ADMIN_ID = 8007670371

# Conversation states
GENDER, NAME, AGE, CITY, PHOTO, MAIN_MENU = range(6)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database("dating.db")


# ─────────────────────────── HELPERS ───────────────────────────

async def check_subscription(user_id: int, bot) -> bool:
    channels = db.get_channels()
    if not channels:
        return True
    for channel in channels:
        try:
            member = await bot.get_chat_member(channel["username"], user_id)
            if member.status in ["left", "kicked", "banned"]:
                return False
        except Exception:
            return False
    return True


async def subscription_keyboard(bot):
    channels = db.get_channels()
    buttons = []
    for ch in channels:
        try:
            chat = await bot.get_chat(ch["username"])
            title = chat.title
        except Exception:
            title = ch["username"]
        link = ch["username"].lstrip("@")
        buttons.append([InlineKeyboardButton(f"📢 {title}", url=f"https://t.me/{link}")])
    buttons.append([InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)


def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("💫 Random topish")],
         [KeyboardButton("👤 Profilim"), KeyboardButton("⚙️ Sozlamalar")]],
        resize_keyboard=True
    )


# ─────────────────────────── START ───────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await check_subscription(user_id, context.bot):
        kb = await subscription_keyboard(context.bot)
        await update.message.reply_text(
            "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
            reply_markup=kb
        )
        return ConversationHandler.END

    user = db.get_user(user_id)
    if user:
        await update.message.reply_text(
            f"👋 Qaytib kelding, *{user['name']}*!\n\nNima qilmoqchisiz?",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    await update.message.reply_text(
        "🌟 *Tanishuv botiga xush kelibsiz!*\n\n"
        "Ro'yxatdan o'tish uchun bir necha savollarga javob bering.\n\n"
        "Jinsingizni tanlang:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👦 Yigit", callback_data="gender_male"),
             InlineKeyboardButton("👧 Qiz", callback_data="gender_female")]
        ])
    )
    return GENDER


async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if not await check_subscription(user_id, context.bot):
        kb = await subscription_keyboard(context.bot)
        await query.edit_message_text(
            "❌ Hali ham obuna bo'lmadingiz. Barcha kanallarga obuna bo'ling:",
            reply_markup=kb
        )
        return

    user = db.get_user(user_id)
    if user:
        await query.edit_message_text("✅ Obuna tasdiqlandi!")
        await context.bot.send_message(
            user_id,
            f"👋 Qaytib kelding, *{user['name']}*!",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
    else:
        await query.edit_message_text(
            "✅ Obuna tasdiqlandi! Endi ro'yxatdan o'ting.\n\nJinsingizni tanlang:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👦 Yigit", callback_data="gender_male"),
                 InlineKeyboardButton("👧 Qiz", callback_data="gender_female")]
            ])
        )


# ─────────────────────────── RO'YXATDAN O'TISH ───────────────────────────

async def gender_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    gender = "male" if query.data == "gender_male" else "female"
    context.user_data["gender"] = gender
    label = "Yigit 👦" if gender == "male" else "Qiz 👧"
    await query.edit_message_text(f"✅ Jinsingiz: {label}\n\nIsm-familiyangizni kiriting:")
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await update.message.reply_text("❌ Ism 2-50 ta belgidan iborat bo'lishi kerak. Qayta kiriting:")
        return NAME
    context.user_data["name"] = name
    await update.message.reply_text(f"✅ Ism: *{name}*\n\nYoshingizni kiriting (raqam):", parse_mode="Markdown")
    return AGE


async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text.strip())
        if age < 16 or age > 60:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Yoshingizni to'g'ri kiriting (16-60 oralig'ida):")
        return AGE
    context.user_data["age"] = age
    await update.message.reply_text(f"✅ Yosh: *{age}*\n\nShahar yoki viloyatingizni kiriting:", parse_mode="Markdown")
    return CITY


async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    context.user_data["city"] = city
    await update.message.reply_text(
        f"✅ Shahar: *{city}*\n\n"
        "📸 Profil rasmingizni yuboring:\n"
        "_(O'tkazib yuborish uchun /skip yozing)_",
        parse_mode="Markdown"
    )
    return PHOTO


async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_id = None
    if update.message.photo:
        photo_id = update.message.photo[-1].file_id

    user_id = update.effective_user.id
    data = context.user_data

    db.add_user(
        user_id=user_id,
        name=data["name"],
        age=data["age"],
        gender=data["gender"],
        city=data["city"],
        photo_id=photo_id,
        username=update.effective_user.username
    )

    gender_label = "Yigit 👦" if data["gender"] == "male" else "Qiz 👧"
    await update.message.reply_text(
        f"🎉 *Ro'yxatdan muvaffaqiyatli o'tdingiz!*\n\n"
        f"👤 Ism: {data['name']}\n"
        f"🎂 Yosh: {data['age']}\n"
        f"📍 Shahar: {data['city']}\n"
        f"⚧ Jins: {gender_label}\n\n"
        f"Endi *💫 Random topish* tugmasi bilan yangi tanishlar toping!",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
    return MAIN_MENU


async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Manually trigger get_photo without a real photo
    update.message.photo = []
    return await get_photo(update, context)


# ─────────────────────────── ASOSIY MENYU ───────────────────────────

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if not await check_subscription(user_id, context.bot):
        kb = await subscription_keyboard(context.bot)
        await update.message.reply_text(
            "⚠️ Botdan foydalanish uchun kanallarga obuna bo'ling:",
            reply_markup=kb
        )
        return MAIN_MENU

    if text == "💫 Random topish":
        await random_match(update, context)
    elif text == "👤 Profilim":
        await show_profile(update, context)
    elif text == "⚙️ Sozlamalar":
        await update.message.reply_text(
            "⚙️ *Sozlamalar*\n\nProfilingizni yangilash uchun /start buyrug'ini bering.",
            parse_mode="Markdown"
        )
    return MAIN_MENU


async def random_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ Avval ro'yxatdan o'ting! /start")
        return

    target_gender = "female" if user["gender"] == "male" else "male"
    candidates = db.get_users_by_gender(target_gender, exclude_id=user_id)

    if not candidates:
        await update.message.reply_text(
            "😔 Hozircha mos foydalanuvchilar topilmadi.\nKo'proq odam qo'shilgach qayta urinib ko'ring!"
        )
        return

    match = random.choice(candidates)
    caption = (
        f"👤 *{match['name']}*\n"
        f"🎂 Yosh: {match['age']}\n"
        f"📍 Shahar: {match['city']}\n"
    )

    buttons = []
    if match.get("username"):
        caption += f"📬 Telegram: @{match['username']}"
        buttons.append([InlineKeyboardButton("💬 Yozish", url=f"https://t.me/{match['username']}")])
    else:
        buttons.append([InlineKeyboardButton("🚫 Username yo'q", callback_data="no_contact")])

    buttons.append([InlineKeyboardButton("🔄 Yana boshqasi", callback_data="random_again")])
    kb = InlineKeyboardMarkup(buttons)

    if match.get("photo_id"):
        await update.message.reply_photo(
            photo=match["photo_id"], caption=caption,
            parse_mode="Markdown", reply_markup=kb
        )
    else:
        await update.message.reply_text(caption, parse_mode="Markdown", reply_markup=kb)


async def random_again_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔄 Yangi odam izlanmoqda...")
    user_id = query.from_user.id
    user = db.get_user(user_id)
    if not user:
        await query.edit_message_text("❌ Avval ro'yxatdan o'ting! /start")
        return

    target_gender = "female" if user["gender"] == "male" else "male"
    candidates = db.get_users_by_gender(target_gender, exclude_id=user_id)

    if not candidates:
        await context.bot.send_message(user_id, "😔 Hozircha boshqa foydalanuvchilar topilmadi.")
        return

    match = random.choice(candidates)
    caption = (
        f"👤 *{match['name']}*\n"
        f"🎂 Yosh: {match['age']}\n"
        f"📍 Shahar: {match['city']}\n"
    )

    buttons = []
    if match.get("username"):
        caption += f"📬 Telegram: @{match['username']}"
        buttons.append([InlineKeyboardButton("💬 Yozish", url=f"https://t.me/{match['username']}")])
    else:
        buttons.append([InlineKeyboardButton("🚫 Username yo'q", callback_data="no_contact")])

    buttons.append([InlineKeyboardButton("🔄 Yana boshqasi", callback_data="random_again")])
    kb = InlineKeyboardMarkup(buttons)

    if match.get("photo_id"):
        await context.bot.send_photo(
            user_id, photo=match["photo_id"], caption=caption,
            parse_mode="Markdown", reply_markup=kb
        )
    else:
        await context.bot.send_message(user_id, caption, parse_mode="Markdown", reply_markup=kb)


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ Profil topilmadi. /start")
        return

    gender_label = "Yigit 👦" if user["gender"] == "male" else "Qiz 👧"
    text = (
        f"👤 *Profilingiz*\n\n"
        f"📝 Ism: {user['name']}\n"
        f"🎂 Yosh: {user['age']}\n"
        f"📍 Shahar: {user['city']}\n"
        f"⚧ Jins: {gender_label}\n"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🗑 Profilni o'chirish", callback_data="delete_profile")]])

    if user.get("photo_id"):
        await update.message.reply_photo(user["photo_id"], caption=text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)


async def delete_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db.delete_user(query.from_user.id)
    await query.edit_message_caption("✅ Profilingiz o'chirildi.\nQayta ro'yxatdan o'tish: /start")


# ─────────────────────────── ADMIN ───────────────────────────

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    channels = db.get_channels()
    ch_list = "\n".join([f"• {c['username']}" for c in channels]) if channels else "Hech qanday kanal yo'q"
    users_count = db.get_users_count()

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Kanal qo'shish", callback_data="admin_add_channel")],
        [InlineKeyboardButton("🗑 Kanal o'chirish", callback_data="admin_del_channel")],
        [InlineKeyboardButton("📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton("📣 Reklama yuborish", callback_data="admin_broadcast")]
    ])
    await update.message.reply_text(
        f"🔐 *Admin Panel*\n\n"
        f"👥 Foydalanuvchilar: *{users_count}*\n\n"
        f"📢 *Majburiy obuna kanallari:*\n{ch_list}",
        parse_mode="Markdown",
        reply_markup=kb
    )


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await query.answer()
    data = query.data

    if data == "admin_add_channel":
        await query.message.reply_text(
            "📢 Kanal username'ini yuboring:\n_(Masalan: @mening_kanalim)_",
            parse_mode="Markdown"
        )
        context.user_data["admin_action"] = "add_channel"

    elif data == "admin_del_channel":
        channels = db.get_channels()
        if not channels:
            await query.message.reply_text("Hech qanday kanal yo'q.")
            return
        buttons = [[InlineKeyboardButton(f"❌ {c['username']}", callback_data=f"delch_{c['username']}")] for c in channels]
        await query.message.reply_text("O'chirmoqchi bo'lgan kanalni tanlang:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("delch_"):
        username = data[6:]
        db.remove_channel(username)
        await query.edit_message_text(f"✅ {username} kanali o'chirildi.")

    elif data == "admin_stats":
        users_count = db.get_users_count()
        male_count = db.get_count_by_gender("male")
        female_count = db.get_count_by_gender("female")
        await query.message.reply_text(
            f"📊 *Statistika*\n\n"
            f"👥 Jami foydalanuvchilar: *{users_count}*\n"
            f"👦 Yigitlar: *{male_count}*\n"
            f"👧 Qizlar: *{female_count}*",
            parse_mode="Markdown"
        )

    elif data == "admin_broadcast":
        await query.message.reply_text(
            "📣 Reklama matnini yuboring:\n_(Rasm ham qo'shishingiz mumkin)_",
            parse_mode="Markdown"
        )
        context.user_data["admin_action"] = "broadcast"

    elif data == "no_contact":
        await query.answer("Bu foydalanuvchining username'i yo'q.", show_alert=True)


async def admin_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    action = context.user_data.get("admin_action")
    if not action:
        return

    if action == "add_channel":
        username = update.message.text.strip()
        if not username.startswith("@"):
            username = "@" + username
        db.add_channel(username)
        await update.message.reply_text(f"✅ *{username}* kanali qo'shildi!", parse_mode="Markdown")
        context.user_data["admin_action"] = None

    elif action == "broadcast":
        all_users = db.get_all_user_ids()
        sent = 0
        failed = 0
        for uid in all_users:
            try:
                if update.message.photo:
                    await context.bot.send_photo(
                        uid,
                        update.message.photo[-1].file_id,
                        caption=update.message.caption or ""
                    )
                else:
                    await context.bot.send_message(uid, update.message.text)
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(
            f"📣 *Reklama natijasi:*\n✅ Yuborildi: {sent}\n❌ Xato: {failed}",
            parse_mode="Markdown"
        )
        context.user_data["admin_action"] = None


# ─────────────────────────── MAIN ───────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GENDER: [
                CallbackQueryHandler(gender_selected, pattern="^gender_"),
                CallbackQueryHandler(check_sub_callback, pattern="^check_sub$"),
            ],
            NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            AGE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            CITY:  [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
            PHOTO: [
                MessageHandler(filters.PHOTO, get_photo),
                CommandHandler("skip", skip_photo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_photo),
            ],
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_handler),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="^check_sub$"))
    app.add_handler(CallbackQueryHandler(random_again_callback, pattern="^random_again$"))
    app.add_handler(CallbackQueryHandler(delete_profile_callback, pattern="^delete_profile$"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^(admin_|delch_|no_contact)"))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, admin_message_handler))

    logger.info("Bot ishga tushdi ✅")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
