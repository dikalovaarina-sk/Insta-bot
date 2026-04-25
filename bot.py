import os
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes


# ---------- HTTP сервер (чтобы Render не падал) ----------
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")


def run_http():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("", port), Handler)
    server.serve_forever()


# запускаем сервер в фоне
threading.Thread(target=run_http).start()


# ---------- токен ----------
TOKEN = os.getenv("TELEGRAM_TOKEN")


# ---------- обработка сообщений ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

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

        # --- тут пока просто отправляем обратно (потом вставим генерацию картинки) ---
        await message.reply_photo(photo=photo_url, caption=caption_text.strip())

    else:
        await message.reply_text("Отправь фото с текстом")


# ---------- запуск бота ----------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.ALL, handle_message))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()