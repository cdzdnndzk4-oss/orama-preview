"""Conservative, local studio-photo draft for owner review.

The source is never modified. This is a heuristic for the ORAMA lightbox,
not a general object-removal model; the owner may retain the original.
"""
import io

import numpy as np
from PIL import Image, ImageFilter, ImageOps

OUTPUT = (800, 600)


def process_photo(data):
    with Image.open(io.BytesIO(data)) as opened:
        if opened.format not in ("JPEG", "PNG"):
            raise ValueError("Επίλεξε JPEG ή PNG")
        opened.draft("RGB", (2400, 2400))
        source = ImageOps.exif_transpose(opened).convert("RGB")
    if source.width * source.height > 20_000_000:
        raise ValueError("Η φωτογραφία έχει υπερβολικά μεγάλη ανάλυση")

    width, height = source.size
    # The lightbox subject sits in its middle. Ignore the textured walls and
    # dark lip at the bottom when finding its extent.
    region = (int(width * .24), int(height * .32), int(width * .73), int(height * .64))
    roi = source.crop(region)
    rgb = np.asarray(roi, dtype=np.float32)
    smooth = np.asarray(roi.filter(ImageFilter.GaussianBlur(19)), dtype=np.float32)
    high = rgb.max(axis=2)
    low = rgb.min(axis=2)
    contrast = np.max(np.abs(rgb - smooth), axis=2)
    saturated = (high - low > 22) & (high > 80)
    dark = high < 142
    ink = dark | saturated | (contrast > 19)
    # The right reflector begins immediately outside the product area in the
    # standard ORAMA lightbox setup; it must not define the product bounds.
    ink[:, int(width * .715) - region[0]:] = False
    # Require some coherent content; a plain lightbox is not a product image.
    yy, xx = np.where(ink)
    if len(xx) < 180:
        raise ValueError("Δεν εντοπίστηκε με ασφάλεια ο σκελετός. Κράτησε την αρχική φωτογραφία.")
    # Ignore isolated highlights/dust at the margins; use wide percentiles,
    # then retain generous padding for pale rims and transparent lenses.
    x1, x2 = np.percentile(xx, [1, 99]).astype(int)
    y1, y2 = np.percentile(yy, [1, 99]).astype(int)
    if x2 - x1 < roi.width * .2 or y2 - y1 < 15:
        raise ValueError("Ο αυτόματος εντοπισμός δεν είναι αξιόπιστος. Κράτησε την αρχική φωτογραφία.")
    pad_x = max(10, int((x2 - x1) * .025))
    pad_y = max(15, int((y2 - y1) * .10))
    box = (max(0, x1-pad_x), max(0, y1-pad_y), min(roi.width, x2+pad_x), min(roi.height, y2+pad_y))
    crop = roi.crop(box)
    pixels = np.asarray(crop, dtype=np.float32)
    # Normalize the studio's grey/white exposure by row. This operates on
    # the ORIGINAL pixels; it does not invent a new lens edge or re-render
    # brand markings. The bright 90th percentile estimates the lightbox.
    background = np.percentile(pixels, 90, axis=1)
    smoothed = np.empty_like(background)
    for row in range(len(background)):
        smoothed[row] = np.median(background[max(0,row-15):row+16], axis=0)
    difference = np.maximum(smoothed[:, None, :] - pixels - 2, 0)
    cleaned = np.clip(255 - difference * 1.08, 0, 255).astype("uint8")
    cleaned[:, max(0, int(width * .715) - region[0] - box[0]):] = 255
    subject = Image.fromarray(cleaned, "RGB")
    target_w = int(OUTPUT[0] * .90)
    target_h = int(OUTPUT[1] * .73)
    scale = min(target_w / subject.width, target_h / subject.height)
    subject = subject.resize((round(subject.width * scale), round(subject.height * scale)), Image.Resampling.LANCZOS)
    result = Image.new("RGB", OUTPUT, "white")
    result.paste(subject, ((OUTPUT[0]-subject.width)//2, (OUTPUT[1]-subject.height)//2))
    output = io.BytesIO()
    result.save(output, format="PNG", optimize=True)
    return output.getvalue(), {"width": OUTPUT[0], "height": OUTPUT[1], "fill_percent": round((x2-x1)*scale/OUTPUT[0]*100)}
