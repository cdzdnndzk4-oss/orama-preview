"""Synthetic lightbox photo for CI; never substituted for human pilot review."""
import io

from PIL import Image, ImageDraw


def lightbox_photo():
    image = Image.new("RGB", (2048, 1536), (195, 195, 193))
    draw = ImageDraw.Draw(image)
    draw.ellipse((650, 770, 1000, 980), outline=(66, 59, 56), width=8)
    draw.ellipse((1040, 770, 1390, 980), outline=(67, 60, 58), width=8)
    draw.line((1000, 820, 1040, 820), fill=(98, 75, 57), width=8)
    draw.line((650, 810, 610, 790), fill=(105, 79, 53), width=8)
    draw.line((1390, 810, 1430, 790), fill=(105, 79, 53), width=8)
    out = io.BytesIO()
    image.save(out, "JPEG", quality=95)
    return out.getvalue()
