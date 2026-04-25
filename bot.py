import os
import requests
import asyncio
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# загружаем .env
load_dotenv()

TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_server():
    server = HTTPServer(('0.0.0.0', 10000), Handler)
    server.serve_forever()

threading.Thread(target=run_server).start()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if message.photo:
        photo = message.photo[-1]
        file = await context.bot.get_file(photo.file_id)

        photo_url = file.file_path
        text = message.caption if message.caption else "Без текста"

        data = {
            "image_url": photo_url,
            "text1": text,
            "text2": ""
        }

        try:
            requests.post(WEBHOOK_URL, json=data)
            await message.reply_text("✅ Пост отправлен в Instagram")
        except Exception as e:
            await message.reply_text("❌ Ошибка отправки")

    else:
        await message.reply_text("❗ Отправь фото с подписью")


async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    print("Бот запущен...")

    await app.initialize()
    await app.start()

    # держим процесс живым
    while True:
        await asyncio.sleep(1000)


if __name__ == "__main__":
    asyncio.run(main())