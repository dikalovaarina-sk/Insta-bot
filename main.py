from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import shutil
import cloudinary
import cloudinary.uploader
import requests
from textwrap import wrap

# Cloudinary настройка
cloudinary.config(
    cloud_name="dsl3vvzs3",
    api_key="758588193925382",
    api_secret="CvdQLB18PASugfnTP5eVP-z2qLY"
)

app = FastAPI()

# перенос текста
def draw_multiline_text(draw, text, font, max_width):
    lines = []
    for line in text.split('\n'):
        lines.extend(wrap(line, width=20))
    return lines

# квадрат + размытие
def make_square(image):
    width, height = image.size
    size = max(width, height)

    bg = image.resize((size, size))
    bg = bg.filter(ImageFilter.GaussianBlur(20))

    bg.paste(image, ((size - width)//2, (size - height)//2))
    return bg

# генерация поста
def create_post(image_path, text1, text2):
    img = Image.open(image_path).convert("RGB")
    img = make_square(img)
    img = img.convert("RGBA")

    width, height = img.size

    overlay = Image.new("RGBA", img.size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)

    box_width = int(width * 0.8)
    box_height = int(height * 0.3)

    x1 = (width - box_width) // 2
    y1 = height // 2 - box_height // 2
    x2 = x1 + box_width
    y2 = y1 + box_height

    draw.rounded_rectangle(
        [x1, y1, x2, y2],
        radius=40,
        fill=(0, 0, 0, 200)
    )

    font1 = ImageFont.truetype("arialbd.ttf", 60)
    font2 = ImageFont.truetype("arialbd.ttf", 70)

    lines1 = draw_multiline_text(draw, text1, font1, box_width)
    lines2 = draw_multiline_text(draw, text2, font2, box_width)

    y_text = y1 + 50

    for line in lines1:
        w, h = draw.textbbox((0,0), line, font=font1)[2:]
        draw.text((width//2 - w//2, y_text), line, font=font1, fill="white")
        y_text += h + 5

    y_text += 10

    for line in lines2:
        w, h = draw.textbbox((0,0), line, font=font2)[2:]
        draw.text((width//2 - w//2, y_text), line, font=font2, fill=(255,200,0))
        y_text += h + 5

    result = Image.alpha_composite(img, overlay).convert("RGB")
    result.save("result.jpg")

    return "result.jpg"

# загрузка в интернет
def upload_image(path):
    res = cloudinary.uploader.upload(path)
    return res["secure_url"]

# постинг (пока не используем)
def post_to_instagram(image_url, caption, access_token, ig_user_id):
    url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media"
    
    params = {
        "image_url": image_url,
        "caption": caption,
        "access_token": access_token
    }

    res = requests.post(url, params=params)
    creation_id = res.json()["id"]

    publish_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish"
    
    publish_params = {
        "creation_id": creation_id,
        "access_token": access_token
    }

    requests.post(publish_url, params=publish_params)

# главный endpoint
@app.post("/generate")
async def generate(
    text1: str = Form(...),
    text2: str = Form(...),
    file: UploadFile = File(...)
):
    with open("temp.jpg", "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    output = create_post("temp.jpg", text1, text2)

    # 🔥 загрузка в интернет
    image_url = upload_image(output)
    print("ССЫЛКА НА КАРТИНКУ:", image_url)
    send_to_make(image_url, text1, text2)

    return FileResponse(output, media_type="image/jpeg")

def send_to_make(image_url, text1, text2):
    print("ОТПРАВКА В MAKE")

    webhook_url = "https://hook.eu1.make.com/dmwb3yah7wjfevybfoeg19zpfrq7ivxq"

    data = {
        "image_url": image_url,
        "text1": text1,
        "text2": text2
    }

    response = requests.post(webhook_url, json=data)
    print("СТАТУС:", response.status_code)