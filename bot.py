import os, io, asyncio
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional, List

from telegram import Update, InputMediaPhoto
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

from translators import get_translator
from ocr_and_render import run_ocr, render_over_image

from utils import AlbumCollector

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
assert TELEGRAM_TOKEN, "Please set TELEGRAM_TOKEN in .env"

translator = get_translator()
collector = AlbumCollector(timeout_sec=3)

HELP_TEXT = (
    "👋 សួស្តី! ផ្ញើរូបភាព (ឬ album រូបភាព) មកខ្ញុំ\n"
    "ខ្ញុំនឹង OCR (EN/ZH/ID/KR) ហើយបកប្រែជាខ្មែរ 📝→ បន្តក់ជាលើរូប\n\n"
    "Commands:\n"
    "/start - ស្វាគមន៍\n"
    "/help - ព័ត៌មានប្រើប្រាស់\n"
    "/text - បង្ហាញលទ្ធផលជាអត្ថបទ (មិនសរសេរលើរូប)\n"
    "/image - បង្ហាញលទ្ធផលជារូប (លំនាំដើម)\n"
)

class UserPref(BaseModel):
    render_mode: str = "image"  # "image" or "text"

user_prefs = {}

def get_pref(user_id: int) -> UserPref:
    return user_prefs.get(user_id, UserPref())

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("សូមស្វាគមន៍! 🎉 " + HELP_TEXT)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)

async def cmd_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prefs[update.effective_user.id] = UserPref(render_mode="text")
    await update.message.reply_text("របៀបបង្ហាញលទ្ធផល: 📝 អត្ថបទ")

async def cmd_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prefs[update.effective_user.id] = UserPref(render_mode="image")
    await update.message.reply_text("របៀបបង្ហាញលទ្ធផល: 🖼️ រូបភាព")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.photo:
        return

    # Download the best-quality photo
    photo = msg.photo[-1]
    file = await photo.get_file()
    img_bytes = await file.download_as_bytearray()

    # If part of an album (media_group_id), collect
    mgid = msg.media_group_id
    if mgid:
        collector.add(mgid, bytes(img_bytes))
        # schedule a flush after timeout
        await asyncio.sleep(3.2)
        items = collector.pop_if_ready(mgid)
        if items:
            await process_images(update, context, items)
    else:
        await process_images(update, context, [bytes(img_bytes)])

async def process_images(update: Update, context: ContextTypes.DEFAULT_TYPE, images: List[bytes]):
    user_id = update.effective_user.id
    pref = get_pref(user_id)

    if pref.render_mode == "text":
        texts = []
        for img in images:
            ocr_items = run_ocr(img)
            joined = "\n".join(t for t, _, conf in ocr_items if t.strip())
            km = translator.translate(joined, target="km") if joined.strip() else ""
            texts.append(km.strip() or "(មិនមានអត្ថបទ)")
        # Reply as a combined text
        out = "\n\n—\n\n".join(texts)
        await update.message.reply_text(out[:4000] or "(ទទេ)")
        return

    # render_mode == "image"
    media = []
    for img in images:
        ocr_items = run_ocr(img)
        source_text = "\n".join(t for t, _, conf in ocr_items if t.strip())
        km_text = translator.translate(source_text, target="km") if source_text.strip() else ""
        rendered = render_over_image(img, ocr_items, km_text)
        media.append(InputMediaPhoto(media=io.BytesIO(rendered)))

    if len(media) == 1:
        await update.message.reply_photo(photo=media[0].media)
    else:
        # Telegram allows up to 10 media per album
        await update.message.reply_media_group(media=media[:10])

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("text", cmd_text))
    app.add_handler(CommandHandler("image", cmd_image))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    print("Bot is running...")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
