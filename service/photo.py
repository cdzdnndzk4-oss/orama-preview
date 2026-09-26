"""Deterministic lightbox normalization; keeps source pixels, never draws a frame.

This is a proposal only. Transparent/pale frames may be rejected or require the
original/manual override. Every processed image remains unpublished by default.
"""
import io
import numpy as np
from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError

CANVAS = (1200, 900)


def process_photo(data: bytes):
    try:
        with Image.open(io.BytesIO(data)) as opened:
            if opened.format not in ("JPEG", "PNG"):
                raise ValueError("Επίλεξε JPEG ή PNG")
            opened.draft("RGB", (2600, 2600))
            source = ImageOps.exif_transpose(opened).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Η φωτογραφία δεν διαβάζεται") from exc
    if source.width * source.height > 24_000_000 or min(source.size) < 500:
        raise ValueError("Μη κατάλληλη ανάλυση φωτογραφίας")

    w, h = source.size
    # Calibrated area inside ORAMA's existing lightbox. Excludes vertical side
    # panels and the black lower edge. If the glasses touch the bounds, fail.
    bounds = (round(w * .22), round(h * .455), round(w * .77), round(h * .69))
    region = source.crop(bounds)
    array = np.asarray(region, dtype=np.float32)
    rh, rw = array.shape[:2]
    # The lightbox is brighter than the subject. Estimate per-row illumination
    # from the 87th percentile, then blend ORIGINAL pixels onto white.
    background = np.percentile(array, 87, axis=1)
    for i in range(3):
        background[:, i] = np.convolve(background[:, i], np.ones(31) / 31, mode="same")
    # Correct convolution margins from nearby interior rows.
    background[:16] = background[16]
    background[-16:] = background[-17]
    difference = np.maximum(background[:, None, :] - array, 0)
    strength = difference.max(2)
    # Strong connected visual signal defines a conservative crop; shadows do
    # not determine crop size. Restrict detection away from softbox seams.
    detection = strength > 34
    detection[:round(rh * .05)] = False
    detection[-round(rh * .05):] = False
    detection[:, :round(rw * .11)] = False
    detection[:, round(rw * .87):] = False
    yy, xx = np.where(detection)
    if len(xx) < 450:
        raise ValueError("Ο σκελετός δεν εντοπίστηκε με ασφάλεια· κράτησε το πρωτότυπο")
    x1, x2 = np.percentile(xx, [0.5, 99.5]).astype(int)
    y1, y2 = np.percentile(yy, [0.5, 99.5]).astype(int)
    if x2 - x1 < rw * .18 or y2 - y1 < rh * .07:
        raise ValueError("Ο αυτόματος εντοπισμός χρειάζεται χειροκίνητο έλεγχο")
    if x1 < rw * .105 or x2 > rw * .875 or y1 < rh * .04 or y2 > rh * .96:
        raise ValueError("Ο σκελετός αγγίζει το όριο της φωτογραφίας· κράτησε το πρωτότυπο")

    pad_x, pad_y = max(30, int((x2 - x1) * .06)), max(22, int((y2 - y1) * .28))
    x1, x2 = max(0, x1 - pad_x), min(int(rw * .88), x2 + pad_x)
    y1, y2 = max(0, y1 - pad_y), min(rh, y2 + pad_y)
    pixels = array[y1:y2, x1:x2]
    bg = background[y1:y2, None, :]
    diff = np.maximum(bg - pixels, 0)
    # The estimated white balance removes the grey lightbox but only subtracts
    # source/background difference. No inpainting or synthetic frame pixels.
    alpha = np.clip((diff.max(2) - 4) / 58, 0, 1)
    # A faint real shadow survives where the source differs slightly from the
    # lightbox. Avoid a hard halo at the crop edge.
    edge = np.minimum.reduce(np.broadcast_arrays(
        np.arange(len(alpha))[:, None], np.arange(len(alpha))[::-1, None],
        np.arange(alpha.shape[1])[None, :], np.arange(alpha.shape[1])[None, ::-1]))
    alpha *= np.clip(edge / 18, 0, 1)
    # Preserve hue of the actual object; white normalization adjusts only the
    # lightbox illumination. Thin metal logos and rim details remain source data.
    normalized = np.clip(pixels + (255 - bg), 0, 255)
    output_pixels = 255 - alpha[..., None] * (255 - normalized)
    cutout = Image.fromarray(output_pixels.clip(0, 255).astype("uint8"), "RGB")
    scale = min(CANVAS[0] * .78 / cutout.width, CANVAS[1] * .55 / cutout.height, 2)
    cutout = cutout.resize((round(cutout.width * scale), round(cutout.height * scale)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", CANVAS, "#FFFFFF")
    canvas.paste(cutout, ((CANVAS[0] - cutout.width) // 2, (CANVAS[1] - cutout.height) // 2))
    output = io.BytesIO()
    canvas.save(output, "PNG", optimize=True)
    return output.getvalue(), {"width": CANVAS[0], "height": CANVAS[1], "subject_width_percent": round(cutout.width / CANVAS[0] * 100), "method": "source-pixels-only", "review_required": True}
