import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# переменные из Render
TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# сюда вставь ID Кати (можно узнать через @userinfobot)
ALLOWED_USER_ID = 123456789


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # защита — только Катя может постить
    if user.id != ALLOWED_USER_ID:
        return

    message = update.message

    # если пришло фото
    if message.photo:
        photo = message.photo[-1]

        file = await context.bot.get_file(photo.file_id)
        photo_url = file.file_path  # ссылка на фото в телеге

        text = message.caption if message.caption else "Без текста"

        data = {
            "image_url": photo_url,
            "text1": text,
            "text2": ""
        }

        # отправка в Make
        try:
            requests.post(WEBHOOK_URL, json=data)
            await message.reply_text("✅ Пост отправлен в Instagram")
        except Exception as e:
            await message.reply_text(f"❌ Ошибка: {e}")

    else:
        await message.reply_text("❗ Отправь фото с подписью")


# запуск бота
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.ALL, handle_message))

print("Бот запущен...")

app.run_polling()