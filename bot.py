import os
import logging
import html
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardRemove, InputMediaPhoto
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
FM_GROUP_CHAT_ID = os.getenv("FM_GROUP_CHAT_ID")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))  # Your Telegram user ID

# Conversation states
REPORT_TYPE, LOCATION, DESCRIPTION, PHOTO = range(4)

LOCATIONS = [
    "Atrium & Lift Lobby",
    "Auditorium",
    "Level 3",
    "Baby Space",
    "Hub",
    "Backstage",
    "Washrooms (Male)",
    "Washrooms (Female)",
    "Storeroom",
    "Others",
]

REPORT_TYPES = {
    "missing": {
        "label": "🛒 Used Up Stock",
        "emoji": "🛒",
        "title": "Used Up Stock",
        "desc_prompt": (
            "What item is missing or has run out? Please describe it clearly.\n\n"
            "Example: Toilet paper rolls, hand soap, mop head"
        ),
        "color": "🟡",
        "needs_location": False,
    },
    "broken": {
        "label": "🔧 Broken Equipment",
        "emoji": "🔧",
        "title": "Broken Equipment",
        "desc_prompt": (
            "What equipment is broken or damaged? Please describe the issue.\n\n"
            "Example: Mop bucket wheel is cracked, cloth handle is bent"
        ),
        "color": "🔴",
        "needs_location": False,
    },
    "issue": {
        "label": "⚠️ Unresolved Issue",
        "emoji": "⚠️",
        "title": "Unresolved Issue",
        "desc_prompt": (
            "What issue did you notice? What did you try?\n\n"
            "Example: Light flickering in Hub, couldn't find the right switch"
        ),
        "color": "🟠",
        "needs_location": True,
    },
}

# ─────────────────────────────────────────────
# CLEANING GUIDE
#
# To add photos to a topic:
# 1. Send /addphoto to the bot (you must be the admin)
# 2. Send the photo — the bot replies with a file_id
# 3. Paste the file_id string into the "photos" list below
#
# Each topic can have multiple photos — just add more file_id strings.
# Leave the list empty [] if no photos yet.
# ─────────────────────────────────────────────
CLEANING_INSTRUCTIONS = {
    "main_menu": (
        "🧹 <b>Cleaning Guide</b>\n\n"
        "Select a topic below to learn how to use the cleaning equipment properly."
    ),
    "mop": {
        "label": "🪣 Using a Mop after a spill",
        "text": (
            "🪣 <b>Taking the mop from the cabinet</b>\n\n"
            "1. Take the yellow pail and put in 1 pump of Heavenly Lime\n"
            "2. Take one blue mop and bring the yellow pail to fill it up with water in the toilet\n"
            "3. There is a bidet gun you can use under the cabinet in the male toilet, else you can use the shower\n"
            "4. Mop in a figure-8 motion, working backwards\n"
            "5. Wring out fully before mopping dry areas\n"
        ),
        "photos": [
            "AgACAgUAAxkBAAN3aiutXNhcgFKX1Ipf_rTgzGdBbaMAAugQaxuJzGBV_rtQEroBoOMBAAMCAAN5AAM8BA"
            "AgACAgUAAxkBAAN7aiutZV_RU59YOUvmtHWF7e_UDi8AAukQaxuJzGBVDaq-Hm3Gi1sBAAMCAAN5AAM8BA"
        ],
    },
    "cloths": {
        "label": "🧽 Cleaning Table after hangout",
        "text": (
            "🧽 <b>Using the disposable cloths</b>\n\n"
            "1. Take the disinfectant spray bottle along with a disposable cloth\n"
            "2. You can use the cloth multiple times and then dispose the cloth\n"
            "3. Return the disinfectant spray to the cabinet after use\n"
        ),
        "photos": [
            "AgACAgUAAxkBAAODaiutdm0dhAfxFg7zBG-Rd8Tm6VQAAuwQaxuJzGBVzTSlhh4PXPQBAAMCAAN5AAM8BA"
            "AgACAgUAAxkBAAOHaiutgz7SEU3d1EQqH0aro1ImZk8AAu0QaxuJzGBViZ_eixxQ8IsBAAMCAAN5AAM8BA"
        ],
    },
    "returning": {
        "label": "📦 Returning Equipment",
        "text": (
            "📦 <b>Returning Equipment to the Cabinet</b>\n\n"
            "Please return all equipment clean and in good condition:\n\n"
            "1. Clean the mop in the shower cubicle and wring it dry using the pail\n"
            "2. Hang mop head facing down to air dry using the hook beside the cabinet\n"
            "3. Place the mop bucket back into the cabinet\n\n"
            "If anything is damaged or missing, please report it using\n"
            "the /start menu. Thank you! 🙏"
        ),
        "photos": [
            "AgACAgUAAxkBAAN_aiutbt9YX10VrTRp4xgKrmi_fqQAAusQaxuJzGBVxJ3A57PYAkwBAAMCAAN5AAM8BA"
        ],
    },
}


# ─────────────────────────────────────────────
# ADMIN: /addphoto helper
# ─────────────────────────────────────────────

async def addphoto_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if ADMIN_USER_ID and user.id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ You are not authorised to use this command.")
        return

    await update.message.reply_text(
        "📸 Send me a photo and I'll reply with its <b>file_id</b>.\n\n"
        "Copy the file_id and paste it into the <code>photos</code> list "
        "for the relevant topic in <code>bot.py</code>.",
        parse_mode="HTML"
    )
    context.user_data["awaiting_guide_photo"] = True


async def addphoto_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_guide_photo"):
        return

    user = update.effective_user
    if ADMIN_USER_ID and user.id != ADMIN_USER_ID:
        return

    file_id = update.message.photo[-1].file_id
    await update.message.reply_text(
        f"✅ <b>Photo file_id:</b>\n\n<code>{file_id}</code>\n\n"
        "Copy this and paste it into the <code>photos</code> list for the relevant topic in <code>bot.py</code>.",
        parse_mode="HTML"
    )
    context.user_data["awaiting_guide_photo"] = False


# ─────────────────────────────────────────────
# MAIN MENU & REPORT FLOW
# ─────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("🧹 Cleaning Guide", callback_data="cleaning_menu")],
        [InlineKeyboardButton("🛒 Used Up Stock", callback_data="type_missing")],
        [InlineKeyboardButton("🔧 Broken Equipment", callback_data="type_broken")],
        [InlineKeyboardButton("⚠️ Unresolved Issue", callback_data="type_issue")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Hi {html.escape(user.first_name)}! I'm the <b>HOGC FM Cabinet Bot</b>.\n\n"
        "What would you like to do?",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    return REPORT_TYPE


async def report_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    report_type = query.data.replace("type_", "")
    context.user_data["report_type"] = report_type
    rtype = REPORT_TYPES[report_type]

    if rtype["needs_location"]:
        location_buttons = []
        for i in range(0, len(LOCATIONS), 2):
            row = [InlineKeyboardButton(LOCATIONS[i], callback_data=f"loc_{i}")]
            if i + 1 < len(LOCATIONS):
                row.append(InlineKeyboardButton(LOCATIONS[i + 1], callback_data=f"loc_{i+1}"))
            location_buttons.append(row)

        await query.edit_message_text(
            f"{rtype['emoji']} <b>{html.escape(rtype['title'])}</b>\n\n📍 Where in the church is this issue?",
            reply_markup=InlineKeyboardMarkup(location_buttons),
            parse_mode="HTML"
        )
        return LOCATION
    else:
        context.user_data["location"] = None
        await query.edit_message_text(
            f"{rtype['emoji']} <b>{html.escape(rtype['title'])}</b>\n\n"
            f"✏️ {rtype['desc_prompt']}",
            parse_mode="HTML"
        )
        return DESCRIPTION


async def location_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    loc_index = int(query.data.replace("loc_", ""))
    location = LOCATIONS[loc_index]
    context.user_data["location"] = location

    report_type = context.user_data["report_type"]
    rtype = REPORT_TYPES[report_type]

    await query.edit_message_text(
        f"{rtype['emoji']} <b>{html.escape(rtype['title'])}</b> — 📍 {html.escape(location)}\n\n"
        f"✏️ {rtype['desc_prompt']}",
        parse_mode="HTML"
    )
    return DESCRIPTION


async def description_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text

    await update.message.reply_text(
        "📸 Do you have a photo to attach?\n\n"
        "Send a photo now, or type /skip to submit without one.",
        reply_markup=ReplyKeyboardRemove()
    )
    return PHOTO


async def photo_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ignore if this is an admin uploading a guide photo
    if context.user_data.get("awaiting_guide_photo"):
        await addphoto_receive(update, context)
        return PHOTO

    photo = update.message.photo[-1]
    context.user_data["photo_file_id"] = photo.file_id
    await send_report(update, context)
    return ConversationHandler.END


async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["photo_file_id"] = None
    await send_report(update, context)
    return ConversationHandler.END


async def send_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = context.user_data
    rtype = REPORT_TYPES[data["report_type"]]
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    username = f"@{user.username}" if user.username else user.full_name

    location_line = f"📍 <b>Location:</b> {html.escape(data['location'])}\n" if data.get("location") else ""

    report_text = (
        f"{rtype['color']} <b>FM REPORT — {html.escape(rtype['title'].upper())}</b>\n"
        f"{'─' * 30}\n"
        f"{location_line}"
        f"📝 <b>Details:</b> {html.escape(data['description'])}\n"
        f"{'─' * 30}\n"
        f"👤 <b>Reported by:</b> {html.escape(username)}\n"
        f"🕐 <b>Time:</b> {now}"
    )

    photo_id = data.get("photo_file_id")

    try:
        if photo_id:
            await context.bot.send_photo(
                chat_id=FM_GROUP_CHAT_ID,
                photo=photo_id,
                caption=report_text,
                parse_mode="HTML"
            )
        else:
            await context.bot.send_message(
                chat_id=FM_GROUP_CHAT_ID,
                text=report_text,
                parse_mode="HTML"
            )

        await update.message.reply_text(
            "✅ <b>Report submitted!</b>\n\n"
            "The FM team has been notified. Thank you for flagging this! 🙏",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to send report to FM group: {e}")
        await update.message.reply_text(
            "⚠️ Something went wrong sending your report. Please contact the FM team directly."
        )

    context.user_data.clear()


# ─────────────────────────────────────────────
# CLEANING GUIDE HANDLERS
# ─────────────────────────────────────────────

async def cleaning_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton(CLEANING_INSTRUCTIONS["mop"]["label"], callback_data="clean_mop")],
        [InlineKeyboardButton(CLEANING_INSTRUCTIONS["cloths"]["label"], callback_data="clean_cloths")],
        [InlineKeyboardButton(CLEANING_INSTRUCTIONS["returning"]["label"], callback_data="clean_return")],
        [InlineKeyboardButton("« Back to Main Menu", callback_data="back_main")],
    ]
    await query.edit_message_text(
        CLEANING_INSTRUCTIONS["main_menu"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def cleaning_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    topic_map = {
        "clean_mop": "mop",
        "clean_cloths": "cloths",
        "clean_return": "returning",
    }
    topic_key = topic_map.get(query.data)
    topic = CLEANING_INSTRUCTIONS[topic_key]
    photos = topic.get("photos", [])

    back_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("« Back to Cleaning Guide", callback_data="cleaning_menu")]
    ])

    # Send the text instructions (edit the existing message)
    await query.edit_message_text(
        topic["text"],
        reply_markup=back_button,
        parse_mode="HTML"
    )

    # Send photos as a follow-up if any are set
    if photos:
        chat_id = query.message.chat_id
        if len(photos) == 1:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photos[0],
                caption="📸 Reference photo"
            )
        else:
            media_group = [
                InputMediaPhoto(media=file_id, caption=f"📸 Photo {i+1}" if i == 0 else "")
                for i, file_id in enumerate(photos)
            ]
            await context.bot.send_media_group(
                chat_id=chat_id,
                media=media_group
            )


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🧹 Cleaning Guide", callback_data="cleaning_menu")],
        [InlineKeyboardButton("🛒 Used Up Stock", callback_data="type_missing")],
        [InlineKeyboardButton("🔧 Broken Equipment", callback_data="type_broken")],
        [InlineKeyboardButton("⚠️ Unresolved Issue", callback_data="type_issue")],
    ]
    await query.edit_message_text(
        "What would you like to do?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Report cancelled. Type /start to begin again.",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Admin photo helper — outside conversation flow
    app.add_handler(CommandHandler("addphoto", addphoto_start))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("report", start)],
        states={
            REPORT_TYPE: [
                CallbackQueryHandler(report_type_selected, pattern="^type_"),
                CallbackQueryHandler(cleaning_menu, pattern="^cleaning_menu$"),
                CallbackQueryHandler(cleaning_topic, pattern="^clean_(mop|cloths|return)$"),
                CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            ],
            LOCATION: [
                CallbackQueryHandler(location_selected, pattern="^loc_"),
                CallbackQueryHandler(cleaning_menu, pattern="^cleaning_menu$"),
                CallbackQueryHandler(cleaning_topic, pattern="^clean_(mop|cloths|return)$"),
                CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            ],
            DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, description_received),
                CallbackQueryHandler(cleaning_menu, pattern="^cleaning_menu$"),
                CallbackQueryHandler(cleaning_topic, pattern="^clean_(mop|cloths|return)$"),
                CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            ],
            PHOTO: [
                MessageHandler(filters.PHOTO, photo_received),
                CommandHandler("skip", skip_photo),
                CallbackQueryHandler(cleaning_menu, pattern="^cleaning_menu$"),
                CallbackQueryHandler(cleaning_topic, pattern="^clean_(mop|cloths|return)$"),
                CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        per_chat=True,
    )

    app.add_handler(conv_handler)

    # Handle guide photo uploads outside of conversation flow too
    app.add_handler(MessageHandler(
        filters.PHOTO & filters.User(ADMIN_USER_ID) if ADMIN_USER_ID else filters.PHOTO,
        addphoto_receive
    ))

    logger.info("Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
