import os
import io
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont
import easyocr

# Languages for OCR: English, Chinese (Simplified+Traditional), Indonesian, Korean
EASY_LANGS = ["en", "ch_sim", "ch_tra", "id", "ko"]

_reader = None
def get_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(EASY_LANGS, gpu=False)
    return _reader

def run_ocr(image_bytes: bytes) -> List[Tuple[str, Tuple[int,int,int,int], float]]:
    """
    Returns list of (text, bbox(xmin,ymin,xmax,ymax), confidence)
    """
    reader = get_reader()
    result = reader.readtext(image_bytes, detail=1)
    out = []
    for (bbox, text, conf) in result:
        # bbox: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] -> convert to xmin,ymin,xmax,ymax
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        xmin, ymin, xmax, ymax = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
        out.append((text, (xmin, ymin, xmax, ymax), float(conf)))
    return out

def load_font() -> ImageFont.FreeTypeFont:
    font_path = os.getenv("KHMER_FONT_PATH", "/usr/share/fonts/truetype/noto/NotoSansKhmer-Regular.ttf")
    size = int(os.getenv("FONT_SIZE", "36"))
    return ImageFont.truetype(font_path, size)

def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    # naive wrap: split by spaces; Khmer has no spaces often—still OK to paint as-is
    words = text.split(" ")
    if len(words) == 1:
        return text
    lines = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return "\n".join(lines)

def render_over_image(img_bytes: bytes, ocr_items, translated_text: str) -> bytes:
    """
    Simple strategy:
    - draw a semi-transparent box at bottom with translated text (full-paragraph),
      OR replace each bbox (more complex). We'll place one box at bottom for clarity.
    """
    pad = int(os.getenv("DRAW_BOX_PADDING", "24"))
    max_w = int(os.getenv("MAX_IMAGE_WIDTH", "1800"))

    im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    # optional resize if too large
    if im.width > max_w:
        ratio = max_w / im.width
        im = im.resize((int(im.width*ratio), int(im.height*ratio)), Image.LANCZOS)

    draw = ImageDraw.Draw(im, "RGBA")
    font = load_font()

    # Compose one combined Khmer text (join lines detected by OCR → translate → show)
    # But here we already passed translated_text from outside (translated of joined OCR).
    text_block = translated_text.strip()
    if not text_block:
        # nothing to draw; just return original
        out = io.BytesIO()
        im.save(out, format="JPEG", quality=92)
        return out.getvalue()

    margin = pad
    box_w = im.width - 2*margin
    wrapped = wrap_text(draw, text_block, font, box_w)

    # Measure text box height
    # Using multiline_textbbox for precise measurement
    left, top, right, bottom = draw.multiline_textbbox((0,0), wrapped, font=font, spacing=8)
    box_h = (bottom - top) + 2*pad

    # Draw semi-transparent rectangle at bottom
    box_y0 = im.height - box_h - margin
    box_y1 = im.height - margin
    draw.rectangle([(margin, box_y0), (im.width - margin, box_y1)], fill=(0,0,0,160), outline=(255,255,255,128), width=2)

    # Draw text
    text_x = margin + pad
    text_y = box_y0 + pad
    draw.multiline_text((text_x, text_y), wrapped, font=font, fill=(255,255,255,255), spacing=8)

    out = io.BytesIO()
    im.save(out, format="JPEG", quality=92)
    return out.getvalue()
