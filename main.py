import os
import re
import shutil
import requests
import cloudinary
import cloudinary.uploader

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse
from PIL import Image, ImageDraw, ImageFont, ImageFilter


cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("CLOUD_API_KEY"),
    api_secret=os.getenv("CLOUD_API_SECRET")
)

app = FastAPI()


def clean_text_for_image(text: str) -> str:
    # убираем эмодзи, потому что arialbd.ttf рисует их как квадрат □
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)
    return text.strip()


def make_square(image: Image.Image) -> Image.Image:
    width, height = image.size
    size = max(width, height)

    bg = image.resize((size, size))
    bg = bg.filter(ImageFilter.GaussianBlur(22))

    bg.paste(image, ((size - width) // 2, (size - height) // 2))
    return bg


def load_font(size: int):
    for font_path in ["arialbd.ttf", "Arial Bold.ttf", "arial.ttf"]:
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass

    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def wrap_text_by_pixels(draw: ImageDraw.ImageDraw, text: str, font, max_width: int):
    lines = []

    for raw_line in text.split("\n"):
        words = raw_line.split()

        if not words:
            lines.append("")
            continue

        current = ""

        for word in words:
            test = word if not current else current + " " + word
            w, _ = text_size(draw, test, font)

            if w <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

    return lines


def fit_text(draw, text, max_width, max_height, start_size, min_size):
    size = start_size

    while size >= min_size:
        font = load_font(size)
        lines = wrap_text_by_pixels(draw, text, font, max_width)

        line_gap = max(6, size // 7)
        total_height = 0

        for line in lines:
            _, h = text_size(draw, line, font)
            total_height += h

        total_height += line_gap * max(0, len(lines) - 1)

        if total_height <= max_height:
            return font, lines, line_gap, total_height

        size -= 2

    font = load_font(min_size)
    lines = wrap_text_by_pixels(draw, text, font, max_width)
    line_gap = 5

    total_height = 0
    for line in lines:
        _, h = text_size(draw, line, font)
        total_height += h
    total_height += line_gap * max(0, len(lines) - 1)

    return font, lines, line_gap, total_height


def draw_centered_lines(draw, lines, font, color, x1, x2, y_start, line_gap):
    y = y_start

    for line in lines:
        w, h = text_size(draw, line, font)
        x = x1 + ((x2 - x1) - w) // 2
        draw.text((x, y), line, font=font, fill=color)
        y += h + line_gap

    return y


def create_post(image_path, text1, text2):
    text1 = clean_text_for_image(text1)
    text2 = clean_text_for_image(text2)

    img = Image.open(image_path).convert("RGB")
    img = make_square(img).convert("RGBA")

    width, height = img.size

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    box_width = int(width * 0.82)
    box_height = int(height * 0.28)

    x1 = (width - box_width) // 2
    y1 = int(height * 0.40)
    x2 = x1 + box_width
    y2 = y1 + box_height

    draw.rounded_rectangle(
        [x1, y1, x2, y2],
        radius=36,
        fill=(0, 0, 0, 185)
    )

    padding_x = int(box_width * 0.08)
    padding_y = int(box_height * 0.14)

    inner_x1 = x1 + padding_x
    inner_x2 = x2 - padding_x
    inner_width = inner_x2 - inner_x1
    inner_height = box_height - padding_y * 2

    top_h = int(inner_height * 0.46)
    bottom_h = inner_height - top_h

    font1, lines1, gap1, total_h1 = fit_text(
        draw=draw,
        text=text1,
        max_width=inner_width,
        max_height=top_h,
        start_size=60,
        min_size=28
    )

    font2, lines2, gap2, total_h2 = fit_text(
        draw=draw,
        text=text2,
        max_width=inner_width,
        max_height=bottom_h,
        start_size=70,
        min_size=30
    )

    y_top_area = y1 + padding_y
    y_bottom_area = y1 + padding_y + top_h

    y_text1 = y_top_area + max(0, (top_h - total_h1) // 2)
    y_text2 = y_bottom_area + max(0, (bottom_h - total_h2) // 2)

    draw_centered_lines(
        draw=draw,
        lines=lines1,
        font=font1,
        color="white",
        x1=inner_x1,
        x2=inner_x2,
        y_start=y_text1,
        line_gap=gap1
    )

    draw_centered_lines(
        draw=draw,
        lines=lines2,
        font=font2,
        color=(255, 200, 0),
        x1=inner_x1,
        x2=inner_x2,
        y_start=y_text2,
        line_gap=gap2
    )

    result = Image.alpha_composite(img, overlay).convert("RGB")
    output_path = "result.jpg"
    result.save(output_path, "JPEG", quality=95)

    return output_path


def upload_image(path):
    res = cloudinary.uploader.upload(
        path,
        resource_type="image",
        format="jpg"
    )
    return res["secure_url"].replace("/upload/", "/upload/f_jpg/")


def send_to_make(image_url, text1, text2):
    print("ОТПРАВКА В MAKE", flush=True)

    webhook_url = os.getenv("WEBHOOK_URL")

    data = {
        "image_url": image_url,
        "text1": text1,
        "text2": text2,
        "caption": text2
    }

    response = requests.post(webhook_url, json=data, timeout=20)
    print("СТАТУС:", response.status_code, flush=True)
    print("ОТВЕТ MAKE:", response.text, flush=True)


@app.post("/generate")
async def generate(
    text1: str = Form(...),
    text2: str = Form(...),
    file: UploadFile = File(...)
):
    with open("temp.jpg", "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    output = create_post("temp.jpg", text1, text2)

    image_url = upload_image(output)
    print("ССЫЛКА НА КАРТИНКУ:", image_url, flush=True)

    send_to_make(image_url, text1, text2)

    return FileResponse(output, media_type="image/jpeg")