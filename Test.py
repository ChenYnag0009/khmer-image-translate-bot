                    suffix = Path(img_url).suffix or ".jpg"
                    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
                    with os.fdopen(fd, "wb") as f:
                        f.write(r.content)
                    with open(tmp_path, "rb") as f:
                        await msg.reply_photo(photo=InputFile(f))
                    os.unlink(tmp_path)
                    sent += 1
                except Exception as e:
                    await msg.reply_text(f"បញ្ហា({img_url}): {e}")
            if sent == 0:
                await msg.reply_text("មិនបានរូបភាពជាមួយ Photo Mode!")
        except Exception as e:
            await msg.reply_text(f"បញ្ហា scrape TikTok Photo Mode: {e}")
        return

    await msg.reply_text("កំពុង download TikTok video...")
    try:
        paths, tmpdir = download_tiktok_video(tiktok_url)
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
                    sent_files += 1
                elif ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                    with path.open("rb") as f:
                        await msg.reply_photo(photo=InputFile(f))
                    sent_files += 1
            except Exception as e:
                await msg.reply_text(f"បញ្ហាចែកចាយ file: {e}")
        if sent_files == 0:
            await msg.reply_text("មិនលិចឃើញ Video/Photo!")
    except Exception as e:
        await msg.reply_text(f"Error TikTok download: {e}")
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
