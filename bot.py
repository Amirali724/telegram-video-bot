import os
import asyncio

from flask import Flask
from threading import Thread

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from telegram.error import TelegramError


# =========================================================
# تنظیمات
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
VIDEO_FILE_ID = os.getenv("VIDEO_FILE_ID")

PORT = int(os.getenv("PORT", "10000"))


# =========================================================
# پنج کانال
# =========================================================

CHANNELS = [
    {
        "username": "@kolbevatani",
        "name": "کلبه وطنی",
        "link": "https://t.me/kolbevatani",
    },
    {
        "username": "@kolbevatanizapas",
        "name": "کلبه وطنی زاپاس",
        "link": "https://t.me/kolbevatanizapas",
    },
    {
        "username": "@ZarakhshRemix",
        "name": "Zarakhsh Remix",
        "link": "https://t.me/ZarakhshRemix",
    },
    {
        "username": "@Loovely_poem",
        "name": "Loovely Poem",
        "link": "https://t.me/Loovely_poem",
    },
    {
        "username": "@Hashashin_text",
        "name": "Hashashin Text",
        "link": "https://t.me/Hashashin_text",
    },
]


# =========================================================
# سرور کوچک برای Render
# =========================================================

app_web = Flask(__name__)


@app_web.route("/")
def home():
    return "Telegram bot is running!"


def run_web_server():
    app_web.run(
        host="0.0.0.0",
        port=PORT
    )


# =========================================================
# نمایش کانال‌ها
# =========================================================

async def show_join_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = (
        "🔐 برای دریافت فیلم، ابتدا در هر ۵ کانال زیر عضو شوید.\n\n"
        "بعد از عضویت در همه کانال‌ها، "
        "روی دکمه «✅ بررسی عضویت» بزنید."
    )

    keyboard = []

    for channel in CHANNELS:

        keyboard.append([
            InlineKeyboardButton(
                f"📢 {channel['name']}",
                url=channel["link"]
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "✅ بررسی عضویت",
            callback_data="check_membership"
        )
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:

        await update.message.reply_text(
            text,
            reply_markup=reply_markup
        )

    elif update.callback_query:

        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup
        )


# =========================================================
# بررسی عضویت
# =========================================================

async def check_membership(
    user_id,
    context
):

    not_joined = []

    for channel in CHANNELS:

        try:

            member = await context.bot.get_chat_member(
                chat_id=channel["username"],
                user_id=user_id
            )

            if member.status in [
                "member",
                "administrator",
                "creator"
            ]:
                continue

            if member.status in [
                "left",
                "kicked"
            ]:
                not_joined.append(channel["name"])

        except TelegramError:

            not_joined.append(channel["name"])

    return not_joined


# =========================================================
# /start
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await show_join_message(
        update,
        context
    )


# =========================================================
# دریافت فیلم از ادمین و نمایش File ID
# =========================================================

async def get_video_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    if not update.message.video:
        return

    video_id = update.message.video.file_id

    await update.message.reply_text(
        "✅ File ID فیلم شما:\n\n"
        f"`{video_id}`\n\n"
        "این مقدار را در Render داخل VIDEO_FILE_ID قرار بده.",
        parse_mode="Markdown"
    )


# =========================================================
# بررسی عضویت
# =========================================================

async def check_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    not_joined = await check_membership(
        user_id,
        context
    )

    # -----------------------------------------------------
    # عضویت کامل است
    # -----------------------------------------------------

    if not not_joined:

        if not VIDEO_FILE_ID:

            await query.edit_message_text(
                "❌ هنوز فیلم برای ربات تنظیم نشده است."
            )

            return

        await query.edit_message_text(
            "✅ عضویت شما تأیید شد.\n\n"
            "🎬 فیلم در حال ارسال است..."
        )

        try:

            video_message = await context.bot.send_video(
                chat_id=user_id,
                video=VIDEO_FILE_ID,
                caption=(
                    "🎬 فیلم را در «پیام‌های ذخیره‌شده» "
                    "خود ارسال کنید.\n\n"
                    "⏳ این فیلم تا ۳۰ ثانیه دیگر "
                    "از این چت پاک می‌شود."
                )
            )

            info_message = await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "⚠️ توجه:\n\n"
                    "فیلم را همین الان به "
                    "«پیام‌های ذخیره‌شده» خود فوروارد کنید.\n\n"
                    "⏳ فقط ۳۰ ثانیه فرصت دارید."
                )
            )

            # 30 ثانیه صبر
            await asyncio.sleep(30)

            # حذف فیلم
            try:

                await context.bot.delete_message(
                    chat_id=user_id,
                    message_id=video_message.message_id
                )

            except TelegramError:
                pass

            # حذف پیام هشدار
            try:

                await context.bot.delete_message(
                    chat_id=user_id,
                    message_id=info_message.message_id
                )

            except TelegramError:
                pass

        except TelegramError:

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "❌ هنگام ارسال فیلم مشکلی پیش آمد.\n"
                    "لطفاً دوباره تلاش کنید."
                )
            )

    # -----------------------------------------------------
    # عضویت ناقص است
    # -----------------------------------------------------

    else:

        missing = "\n".join(
            f"❌ {name}"
            for name in not_joined
        )

        text = (
            "⚠️ عضویت شما هنوز کامل نیست.\n\n"
            "عضویت شما در این کانال‌ها تأیید نشده:\n\n"
            f"{missing}\n\n"
            "بعد از عضویت، دوباره دکمه بررسی را بزنید."
        )

        keyboard = []

        for channel in CHANNELS:

            keyboard.append([
                InlineKeyboardButton(
                    f"📢 {channel['name']}",
                    url=channel["link"]
                )
            ])

        keyboard.append([
            InlineKeyboardButton(
                "🔄 بررسی عضویت",
                callback_data="check_membership"
            )
        ])

        reply_markup = InlineKeyboardMarkup(
            keyboard
        )

        await query.edit_message_text(
            text,
            reply_markup=reply_markup
        )


# =========================================================
# اجرای ربات
# =========================================================

def main():

    # اجرای وب‌سرور برای Render
    Thread(
        target=run_web_server,
        daemon=True
    ).start()

    # ساخت ربات
    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # /start
    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # بررسی عضویت
    application.add_handler(
        CallbackQueryHandler(
            check_button,
            pattern="^check_membership$"
        )
    )

    # دریافت فیلم و گرفتن File ID
    application.add_handler(
        MessageHandler(
            filters.VIDEO,
            get_video_id
        )
    )

    print("🤖 Bot is running...")

    application.run_polling()


if __name__ == "__main__":
    main()
