import os
import requests
import cloudinary
import cloudinary.uploader

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

threading.Thread(target=run_server).start()

# --- настройки ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("CLOUD_API_KEY"),
    api_secret=os.getenv("CLOUD_API_SECRET")
)

# --- обработка ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    print("Получено сообщение", flush=True)

    if message.photo:
        try:
            # берем фото
            photo = message.photo[-1]
            file = await context.bot.get_file(photo.file_id)

            # скачиваем
            local_path = "temp.jpg"
            await file.download_to_drive(local_path)

            # грузим в cloudinary
            upload = cloudinary.uploader.upload(
                local_path,
                resource_type="image",
                format="jpg"
            )

            photo_url = upload["secure_url"].replace("/upload/", "/upload/f_jpg/")
            print("Cloudinary URL:", photo_url, flush=True)

            # текст
            text = message.caption if message.caption else ""

            if "---" in text:
                photo_text, caption_text = text.split("---", 1)
            else:
                photo_text = text
                caption_text = text

            # отправка в Make
            response = requests.post(WEBHOOK_URL, json={
                "image_url": photo_url,
                "caption": caption_text.strip()
            }, timeout=20)

            print("Make status:", response.status_code, flush=True)
            print("Make response:", response.text, flush=True)

            await message.reply_text("✅ Пост отправлен в Make")

        except Exception as e:
            await message.reply_text(f"❌ Ошибка: {e}")

    else:
        await message.reply_text("Отправь фото с текстом")

# --- запуск ---
def main():
    import asyncio

    print("START MAIN", flush=True)

    if not TOKEN:
        print("ОШИБКА: TELEGRAM_TOKEN не найден", flush=True)
        return

    if not WEBHOOK_URL:
        print("ОШИБКА: WEBHOOK_URL не найден", flush=True)
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))

    print("Бот запущен и слушает Telegram...", flush=True)
    app.run_polling()

if __name__ == "__main__":
    main()