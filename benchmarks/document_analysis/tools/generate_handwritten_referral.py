"""Имитирует фото рукописного медицинского направления.

PIL рисует текст шрифтом Caveat (handwriting, OFL) на жёлтоватом фоне с
лёгким шумом — приближение к фотографии записки. НЕ настоящий врачебный
почерк, но даёт LLM нестандартный шрифт + визуальный шум.

Запуск:
    python tools/generate_handwritten_referral.py \\
        --out /tmp/doc_handwritten.png \\
        --facility "Поликлиника №7" \\
        --patient "Орлов А.С." \\
        --date "10.03.2026" \\
        --diagnosis "Артериальная гипертензия II ст." \\
        --recommendation "Консультация кардиолога" \\
        --doctor "Лебедев Д.А."
"""

import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_PATH = Path(__file__).resolve().parent / "fonts" / "Caveat-Regular.ttf"


def _paper_bg(width: int, height: int) -> Image.Image:
    base = Image.new("RGB", (width, height), (248, 244, 226))  # тёплый бумажный
    # лёгкая зернистость
    noise = Image.new("L", (width, height))
    px = noise.load()
    rand = random.Random(42)
    for y in range(height):
        for x in range(width):
            px[x, y] = 240 + rand.randint(0, 15)
    base = Image.composite(base, Image.new("RGB", base.size, (255, 250, 235)), noise)
    return base.filter(ImageFilter.GaussianBlur(0.3))


def build(args: argparse.Namespace) -> None:
    if not FONT_PATH.exists():
        raise FileNotFoundError(f"Не нашёл {FONT_PATH}. Скачайте Caveat-Regular.ttf в tools/fonts/")

    W, H = 1200, 1600
    img = _paper_bg(W, H)
    draw = ImageDraw.Draw(img)

    title_font = ImageFont.truetype(str(FONT_PATH), 60)
    head_font = ImageFont.truetype(str(FONT_PATH), 44)
    body_font = ImageFont.truetype(str(FONT_PATH), 40)
    signature_font = ImageFont.truetype(str(FONT_PATH), 50)

    ink = (35, 35, 70)

    y = 80
    draw.text((W // 2 - 220, y), args.facility, font=title_font, fill=ink)
    y += 110

    draw.text((80, y), f"Пациент: {args.patient}", font=head_font, fill=ink)
    y += 70
    draw.text((80, y), f"Дата: {args.date}", font=head_font, fill=ink)
    y += 110

    draw.text((80, y), "Направление", font=title_font, fill=ink)
    y += 100

    draw.text((80, y), "Диагноз:", font=head_font, fill=ink)
    y += 60
    draw.text((100, y), args.diagnosis, font=body_font, fill=ink)
    y += 100

    draw.text((80, y), "Рекомендация:", font=head_font, fill=ink)
    y += 60
    draw.text((100, y), args.recommendation, font=body_font, fill=ink)
    y += 200

    draw.text((W - 600, y), f"Врач: {args.doctor}", font=signature_font, fill=ink)

    # лёгкое размытие имитирует фокус мобильной камеры
    img = img.filter(ImageFilter.GaussianBlur(0.4))
    img.save(args.out, quality=88)
    print(f"✅ {args.out}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    p.add_argument("--facility", default="Поликлиника №7")
    p.add_argument("--patient", default="Орлов А.С.")
    p.add_argument("--date", default="10.03.2026")
    p.add_argument("--diagnosis", required=True)
    p.add_argument("--recommendation", required=True)
    p.add_argument("--doctor", default="Лебедев Д.А.")
    build(p.parse_args())


if __name__ == "__main__":
    main()
