import os
import tempfile
import shutil
from pathlib import Path
from yt_dlp import YoutubeDL

from dotenv import load_dotenv
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "សួស្តី! សូមផ្ញើ TikTok link ដែលអ្នកចង់ទាញយក video ឬ photo."
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "/start - បង្ហាញពត៌មាន
"
        "ផ្ញើ TikTok URL ដើម្បីទាញយកវីដេអូ ឬ រូបភាព"
    )

def download_tiktok_with_ytdlp(url: str) -> list[Path]:
    tmpdir = Path(tempfile.mkdtemp(prefix="tiktok_dl_"))
    ydl_opts = {
        "outtmpl": str(tmpdir / "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "nocheckcertificate": True,
        "quiet": True,
        "no_warnings": True,
        "format": "bestvideo+bestaudio/best",
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return list(tmpdir.iterdir()), tmpdir  # paths and temp folder for cleanup

async def handle_tiktok(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not msg or not msg.text:
        return

    tiktok_url = msg.text.strip()
    await msg.reply_text("កំពុងទាញយក TikTok content សូមរង់ចាំ...")

    try:
        paths, tmpdir = download_tiktok_with_ytdlp(tiktok_url)
        if not paths:
            await msg.reply_text("មិនអាចទាញយកមាតិកា TikTok បានទេ។")
            return

        sent_files = 0
        for path in paths:
            ext = path.suffix.lower()
            try:
                if ext in [".mp4", ".mkv", ".webm"]:
                    with path.open("rb") as f:
                        await msg.reply_video(video=InputFile(f))
                elif ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                    with path.open("rb") as f:
                        await msg.reply_photo(photo=InputFile(f))
                else:
                    continue
                sent_files += 1
            except Exception as e:
                await msg.reply_text(f"មានបញ្ហានៅពេលផ្ញើ file: {e}")

        if sent_files == 0:
            await msg.reply_text("មិនមានមាតិកាដែលអាចផ្ញើបាន។")

    except Exception as e:
        await msg.reply_text(f"មានបញ្ហា ក្នុងការទាញយក TikTok: {e}")

    finally:
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "មិនស្គាល់ពាក្យបញ្ជា។ សូមប្រើ /start ឬ /help ឬផ្ញើ TikTok URL ដោយផ្ទាល់។"
    )

def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN មិនបានកំណត់ក្នុង .env")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tiktok))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("Bot ដំណើរការ...")
    app.run_polling()

if __name__ == "__main__":
    main()
