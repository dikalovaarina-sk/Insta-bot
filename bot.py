import os
import requests
import cloudinary
import cloudinary.uploader
import threading
import asyncio

from http.server import HTTPServer, BaseHTTPRequestHandler
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes


# --- мини-сервер для Render ---
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


threading.Thread(target=run_server, daemon=True).start()


# --- настройки ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("CLOUD_API_KEY"),
    api_secret=os.getenv("CLOUD_API_SECRET")
)


# --- перенос текста ---
def draw_multiline_text(text, max_chars=22):
    lines = []
    for line in text.split("\n"):
        if line.strip():
            lines.extend(wrap(line, width=max_chars))
        else:
            lines.append("")
    return lines


# --- квадрат + размытие ---
def make_square(image):
    width, height = image.size
    size = max(width, height)

    bg = image.resize((size, size))
    bg = bg.filter(ImageFilter.GaussianBlur(20))

    bg.paste(image, ((size - width) // 2, (size - height) // 2))
    return bg


# --- создание картинки с текстом как в Swagger ---
def create_post(image_path, text1, text2):
    img = Image.open(image_path).convert("RGB")
    img = make_square(img)
    img = img.convert("RGBA")

    width, height = img.size

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    box_width = int(width * 0.85)
    box_height = int(height * 0.32)

    x1 = (width - box_width) // 2
    y1 = height // 2 - box_height // 2
    x2 = x1 + box_width
    y2 = y1 + box_height

    draw.rounded_rectangle(
        [x1, y1, x2, y2],
        radius=40,
        fill=(0, 0, 0, 200)
    )

    try:
        font1 = ImageFont.truetype("arialbd.ttf", 60)
        font2 = ImageFont.truetype("arialbd.ttf", 70)
    except:
        font1 = ImageFont.load_default()
        font2 = ImageFont.load_default()

    lines1 = draw_multiline_text(text1, max_chars=22)
    lines2 = draw_multiline_text(text2, max_chars=20)

    y_text = y1 + 45

    for line in lines1:
        bbox = draw.textbbox((0, 0), line, font=font1)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text((width // 2 - w // 2, y_text), line, font=font1, fill="white")
        y_text += h + 8

    y_text += 12

    for line in lines2:
        bbox = draw.textbbox((0, 0), line, font=font2)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text((width // 2 - w // 2, y_text), line, font=font2, fill=(255, 200, 0))
        y_text += h + 8

    result = Image.alpha_composite(img, overlay).convert("RGB")
    output_path = "result.jpg"
    result.save(output_path, "JPEG", quality=95)

    return output_path


# --- обработка сообщений ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    print("Получено сообщение", flush=True)

    if not message.photo:
        await message.reply_text("Отправь фото с текстом")
        return

    try:
        photo = message.photo[-1]
        file = await context.bot.get_file(photo.file_id)

        local_path = "temp.jpg"
        await file.download_to_drive(local_path)

        text = message.caption if message.caption else ""

        # формат:
        # текст на фото
        # ---
        # подпись под постом
        if "///" in text:
            photo_text, caption_text = text.split("///", 1)
        else:
            photo_text = text
            caption_text = text

        photo_text = photo_text.strip()
        caption_text = caption_text.strip()

        # делим текст на 2 части для надписи на фото
        photo_lines = photo_text.split("\n", 1)
        text1 = photo_lines[0].strip() if len(photo_lines) > 0 else ""
        text2 = photo_lines[1].strip() if len(photo_lines) > 1 else ""

        # если второй строки нет, оставляем только первую
        if not text2:
            text2 = ""

        # создаём картинку с текстом
        result_path = create_post(local_path, text1, text2)

        # грузим готовую картинку в Cloudinary
        upload = cloudinary.uploader.upload(
            result_path,
            resource_type="image",
            format="jpg"
        )

        photo_url = upload["secure_url"].replace("/upload/", "/upload/f_jpg/")
        print("Cloudinary URL:", photo_url, flush=True)

        response = requests.post(WEBHOOK_URL, json={
            "image_url": photo_url,
            "caption": caption_text,
            "text1": photo_text,
            "text2": caption_text
        }, timeout=20)

        print("Make status:", response.status_code, flush=True)
        print("Make response:", response.text, flush=True)

        await message.reply_text("✅ Пост отправлен в Make")

    except Exception as e:
        print("Ошибка:", e, flush=True)
        await message.reply_text(f"❌ Ошибка: {e}")


# --- запуск ---
async def main():
    print("START MAIN", flush=True)

    if not TOKEN:
        print("ОШИБКА: TELEGRAM_TOKEN не найден", flush=True)
        return

    if not WEBHOOK_URL:
        print("ОШИБКА: WEBHOOK_URL не найден", flush=True)
        return

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))

    print("Бот запущен и слушает Telegram...", flush=True)

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())