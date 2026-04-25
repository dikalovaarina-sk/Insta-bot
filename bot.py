import os
import requests
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# загрузка .env
load_dotenv()

TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    # если фото
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
        except:
            await message.reply_text("❌ Ошибка при отправке")

    else:
        await message.reply_text("❗ Отправь фото с подписью")


if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    print("Бот запущен...")
    app.run_polling()