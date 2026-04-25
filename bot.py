import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes



class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")


TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    # если пришло фото
    if message.photo:
        photo = message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_url = file.file_path

        text = message.caption if message.caption else ""

        # --- делим текст ---
        if "---" in text:
            photo_text, caption_text = text.split("---", 1)
        else:
            photo_text = text
            caption_text = text

        photo_text = photo_text.strip()
        caption_text = caption_text.strip()

        # делим текст на 2 строки для картинки
        lines = photo_text.split("|")

        text1 = lines[0].strip() if len(lines) > 0 else ""
        text2 = lines[1].strip() if len(lines) > 1 else ""

        data = {
            "image_url": photo_url,
            "text1": text1,
            "text2": text2,
            "caption": caption_text
        }

        # отправляем в Make
        requests.post(WEBHOOK_URL, json=data)

        await message.reply_text("✅ Пост отправлен в Instagram")

    else:
        await message.reply_text("❗ Отправь фото с подписью")


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()