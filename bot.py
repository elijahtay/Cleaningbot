import os
import logging
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardRemove
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
FM_GROUP_CHAT_ID = os.getenv("FM_GROUP_CHAT_ID")  # negative number for groups

# Conversation states
REPORT_TYPE, DESCRIPTION, PHOTO = range(4)

REPORT_TYPES = {
    "missing": {
        "label": "🛒 Missing / Used Up Stock",
        "emoji": "🛒",
        "title": "Missing / Used Up Stock",
        "desc_prompt": (
            "What item is missing or has run out?.\n\n"
            "_Example: Cleaning detergent, Disinfectant Spray, disposable cloths, mop head_"
        ),
        "color": "🟡",
    },
    "broken": {
        "label": "🔧 Broken Equipment",
        "emoji": "🔧",
        "title": "Broken Equipment",
        "desc_prompt": (
            "What equipment is broken or damaged? Please describe the issue.\n\n"
            "_Example: Mop bucket wheel is cracked, mop handle is bent_"
        ),
        "color": "🔴",
    },
    "issue": {
        "label": "⚠️ Unresolved Issue",
        "emoji": "⚠️",
        "title": "Unresolved Issue",
        "desc_prompt": (
            "What issue did you notice? What did you try?\n\n"
            "_Example: Light flickering in IDR Male Toilet"
        ),
        "color": "🟠",
    },
}

# ─────────────────────────────────────────────
# CLEANING INSTRUCTIONS
# Edit the sections below with your actual content
# ─────────────────────────────────────────────
CLEANING_INSTRUCTIONS = {
    "main_menu": (
        "🧹 *Cleaning Instructions*\n\n"
        "Select a topic below to learn how to use the cleaning equipment properly."
    ),
    "mop": {
        "label": "🪣 How to Use the Mop",
        "text": (
            "🪣 *How to Use the Mop*\n\n"
            "1. [Take the Yellow Bucket and put in 1 pump of Heavenly Lime Solution]\n"
            "2. [Bring the pail and blue mop to the washroom and add water]\n"
            "3. [For general areas, use only the blue mops]\n"
            "4. [Mop in a figure-8 motion, working backwards]\n"
            "5. [Once done, pour the dirty water using the shower cubicle and wash it]\n"
            "6. [Bring back the mop to the cabinet and hang it at the side, put the pail back into the cabinet]\n\n"
            "⚠️ *Note:* [Do not place back the wet mop into the cabinet]"
        ),
    },
    "cloths": {
        "label": "🧽 Cleaning the hangout tables",
        "text": (
            "🧽 *How to Use the Cloths*\n\n"
            "1. [Take the bottle of disinfectant spray along with a piece of disposable cloth]\n"
            "2. [Spray and wipe the table, you can use the cloth multiple times before disposing it]\n"
            "3. [Bring back the disinfectant spray to the cabinet.]\n\n"
        ),
    },
}


# ─────────────────────────────────────────────
# HANDLERS
# ─────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton(REPORT_TYPES["missing"]["label"], callback_data="type_missing")],
        [InlineKeyboardButton(REPORT_TYPES["broken"]["label"], callback_data="type_broken")],
        [InlineKeyboardButton(REPORT_TYPES["issue"]["label"], callback_data="type_issue")],
        [InlineKeyboardButton("🧹 Cleaning Instructions", callback_data="cleaning_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Hi {user.first_name}! I'm the *HOGC FM Cabinet Bot*.\n\n"
        "What would you like to do?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return REPORT_TYPE


async def report_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    report_type = query.data.replace("type_", "")
    context.user_data["report_type"] = report_type
    rtype = REPORT_TYPES[report_type]

    # Issues need a location; missing/broken go straight to description
    if rtype["needs_location"]:
        location_buttons = []
        for i in range(0, len(LOCATIONS), 2):
            row = [InlineKeyboardButton(LOCATIONS[i], callback_data=f"loc_{i}")]
            if i + 1 < len(LOCATIONS):
                row.append(InlineKeyboardButton(LOCATIONS[i + 1], callback_data=f"loc_{i+1}"))
            location_buttons.append(row)

        await query.edit_message_text(
            f"{rtype['emoji']} *{rtype['title']}*\n\n📍 Where in the church is this issue?",
            reply_markup=InlineKeyboardMarkup(location_buttons),
            parse_mode="Markdown"
        )
        return LOCATION
    else:
        context.user_data["location"] = None
        await query.edit_message_text(
            f"{rtype['emoji']} *{rtype['title']}*\n\n"
            f"✏️ {rtype['desc_prompt']}",
            parse_mode="Markdown"
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
        f"{rtype['emoji']} *{rtype['title']}* — 📍 {location}\n\n"
        f"✏️ {rtype['desc_prompt']}",
        parse_mode="Markdown"
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

    location_line = f"📍 *Location:* {data['location']}\n" if data.get("location") else ""

    report_text = (
        f"{rtype['color']} *FM REPORT — {rtype['title'].upper()}*\n"
        f"{'─' * 30}\n"
        f"{location_line}"
        f"📝 *Details:* {data['description']}\n"
        f"{'─' * 30}\n"
        f"👤 *Reported by:* {username}\n"
        f"🕐 *Time:* {now}"
    )

    photo_id = data.get("photo_file_id")

    try:
        if photo_id:
            await context.bot.send_photo(
                chat_id=FM_GROUP_CHAT_ID,
                photo=photo_id,
                caption=report_text,
                parse_mode="Markdown"
            )
        else:
            await context.bot.send_message(
                chat_id=FM_GROUP_CHAT_ID,
                text=report_text,
                parse_mode="Markdown"
            )

        await update.message.reply_text(
            "✅ *Report submitted!*\n\n"
            "The FM team has been notified. Thank you for flagging this! 🙏",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to send report to FM group: {e}")
        await update.message.reply_text(
            "⚠️ Something went wrong sending your report. Please contact the FM team directly."
        )

    context.user_data.clear()


# ─────────────────────────────────────────────
# CLEANING INSTRUCTIONS HANDLERS
# ─────────────────────────────────────────────

async def cleaning_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton(CLEANING_INSTRUCTIONS["mop"]["label"], callback_data="clean_mop")],
        [InlineKeyboardButton(CLEANING_INSTRUCTIONS["cloths"]["label"], callback_data="clean_cloths")],
        [InlineKeyboardButton(CLEANING_INSTRUCTIONS["cleaning_process"]["label"], callback_data="clean_process")],
        [InlineKeyboardButton(CLEANING_INSTRUCTIONS["returning"]["label"], callback_data="clean_return")],
        [InlineKeyboardButton("« Back to Main Menu", callback_data="back_main")],
    ]
    await query.edit_message_text(
        CLEANING_INSTRUCTIONS["main_menu"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def cleaning_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    topic_map = {
        "clean_mop": "mop",
        "clean_cloths": "cloths",
        "clean_process": "cleaning_process",
        "clean_return": "returning",
    }
    topic_key = topic_map.get(query.data)
    topic = CLEANING_INSTRUCTIONS[topic_key]

    back_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("« Back to Cleaning Menu", callback_data="cleaning_menu")]
    ])
    await query.edit_message_text(
        topic["text"],
        reply_markup=back_button,
        parse_mode="Markdown"
    )


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton(REPORT_TYPES["missing"]["label"], callback_data="type_missing")],
        [InlineKeyboardButton(REPORT_TYPES["broken"]["label"], callback_data="type_broken")],
        [InlineKeyboardButton(REPORT_TYPES["issue"]["label"], callback_data="type_issue")],
        [InlineKeyboardButton("🧹 Cleaning Instructions", callback_data="cleaning_menu")],
    ]
    await query.edit_message_text(
        "What would you like to do?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
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

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("report", start)],
        states={
            REPORT_TYPE: [
                CallbackQueryHandler(report_type_selected, pattern="^type_"),
                CallbackQueryHandler(cleaning_menu, pattern="^cleaning_menu$"),
                CallbackQueryHandler(cleaning_topic, pattern="^clean_(mop|cloths|process|return)$"),
                CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            ],
            LOCATION: [
                CallbackQueryHandler(location_selected, pattern="^loc_"),
            ],
            DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, description_received),
            ],
            PHOTO: [
                MessageHandler(filters.PHOTO, photo_received),
                CommandHandler("skip", skip_photo),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        per_chat=True,
    )

    app.add_handler(conv_handler)

    logger.info("Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
