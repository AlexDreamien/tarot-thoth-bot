"""Generate the bot's profile icon (a Thoth-tarot motif) with Pillow.

    python tools/generate_icon.py            # -> tools/bot_icon.png (512x512)

Rendered at 4x and downscaled with LANCZOS for smooth edges. Not used at
runtime — it's an asset you upload to @BotFather (/setuserpic). Original art,
no third-party imagery.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent / "bot_icon.png"

SIZE = 512
SS = 4  # supersample factor
S = SIZE * SS

BG_TOP = (78, 38, 116)
BG_BOTTOM = (16, 8, 30)
GOLD = (240, 208, 120)
GOLD_BRIGHT = (255, 232, 168)


def _vertical_gradient(size: int, top, bottom) -> Image.Image:
    img = Image.new("RGB", (size, size), top)
    px = img.load()
    for y in range(size):
        f = y / (size - 1)
        r = int(top[0] + (bottom[0] - top[0]) * f)
        g = int(top[1] + (bottom[1] - top[1]) * f)
        b = int(top[2] + (bottom[2] - top[2]) * f)
        for x in range(size):
            px[x, y] = (r, g, b)
    return img


def _vignette(size: int) -> Image.Image:
    """Dark radial vignette (transparent center, dark edges)."""
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse([-size * 0.15, -size * 0.15, size * 1.15, size * 1.15], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(size * 0.12))
    layer = Image.new("RGBA", (size, size), (8, 4, 16, 200))
    layer.putalpha(Image.eval(mask, lambda v: 200 - int(v * 200 / 255)))
    return layer


def _star_points(cx, cy, outer, inner, n=5, rot=-math.pi / 2):
    pts = []
    for i in range(n):
        a_out = rot + i * 2 * math.pi / n
        a_in = a_out + math.pi / n
        pts.append((cx + outer * math.cos(a_out), cy + outer * math.sin(a_out)))
        pts.append((cx + inner * math.cos(a_in), cy + inner * math.sin(a_in)))
    return pts


def _card(size, w, h, radius, angle, outline, fill):
    """A single rounded-rectangle card silhouette, rotated, on its own layer."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = size / 2, size / 2
    d.rounded_rectangle(
        [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2],
        radius=radius,
        outline=outline,
        width=max(2, size // 260),
        fill=fill,
    )
    return layer.rotate(angle, resample=Image.BICUBIC, center=(cx, cy))


def build() -> Image.Image:
    rng = random.Random(20260722)
    img = _vertical_gradient(S, BG_TOP, BG_BOTTOM).convert("RGBA")

    # Constellation dots.
    stars = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ds = ImageDraw.Draw(stars)
    for _ in range(90):
        x, y = rng.uniform(0, S), rng.uniform(0, S)
        r = rng.uniform(S * 0.0015, S * 0.006)
        a = rng.randint(40, 150)
        ds.ellipse([x - r, y - r, x + r, y + r], fill=(255, 240, 200, a))
    img = Image.alpha_composite(img, stars)

    cx = cy = S / 2

    # Three fanned cards behind the star (the three-card spread motif).
    cw, ch, cr = S * 0.30, S * 0.46, S * 0.03
    for angle, dy in ((20, 0.02), (-20, 0.02), (0, 0.0)):
        card = _card(
            S,
            cw,
            ch,
            cr,
            angle,
            outline=(*GOLD, 120),
            fill=(120, 70, 150, 55),
        )
        offset = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        offset.paste(card, (0, int(S * dy)))
        img = Image.alpha_composite(img, offset)

    # Central star with a soft glow.
    outer, inner = S * 0.20, S * 0.082
    pts = _star_points(cx, cy - S * 0.01, outer, inner)

    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(glow).polygon(pts, fill=(255, 220, 150, 200))
    glow = glow.filter(ImageFilter.GaussianBlur(S * 0.03))
    img = Image.alpha_composite(img, glow)

    star = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dstar = ImageDraw.Draw(star)
    dstar.polygon(pts, fill=(*GOLD, 255), outline=(*GOLD_BRIGHT, 255))
    # inner highlight
    inner_pts = _star_points(cx, cy - S * 0.01, outer * 0.62, inner * 0.62)
    dstar.polygon(inner_pts, fill=(*GOLD_BRIGHT, 255))
    img = Image.alpha_composite(img, star)

    # Thin decorative ring, kept inside the circle Telegram crops to.
    ring = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ring)
    m = S * 0.055
    dr.ellipse([m, m, S - m, S - m], outline=(*GOLD, 90), width=max(2, S // 340))
    img = Image.alpha_composite(img, ring)

    img = Image.alpha_composite(img, _vignette(S))

    return img.convert("RGB").resize((SIZE, SIZE), Image.LANCZOS)


def main() -> None:
    build().save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
