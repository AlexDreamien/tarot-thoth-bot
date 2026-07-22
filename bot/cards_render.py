"""Render Thoth cards to images (Pillow) — an original vector deck.

Thin IO/presentation layer, not unit-tested. Every card is drawn procedurally
in a single cohesive style: an element-tinted gradient, a gilt double border
with corner flourishes, faint star-dust, a title band, and a central emblem —
classic pip layouts for the small cards, heraldic medallions for the courts,
and a bespoke symbol for each Major Arcanum. Rendered at 3x and downscaled
(LANCZOS) for smooth edges.

This is the source of the bundled assets (``tools/generate_cards.py``) and the
runtime fallback when an asset PNG is missing. :func:`compose` tiles the drawn
cards into one image for Telegram. All art is original — no third-party imagery.

Swap in different art by replacing the PNGs in ``assets/cards/`` — the ids /
filenames and this module's interface stay the same.
"""

from __future__ import annotations

import io
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .deck import Card, get_card

ASSET_DIR = Path(__file__).resolve().parent.parent / "assets" / "cards"

CARD_W, CARD_H = 360, 600
_MARGIN = 24
_GAP = 20
_SS = 3  # supersample factor for smooth edges

GOLD = (238, 202, 128)
GOLD_HI = (255, 236, 176)

# element / arcana palette: background gradient (top, bottom) + emblem colour
_PALETTE = {
    "fire": ((96, 20, 24), (26, 6, 10), (250, 176, 96)),
    "water": ((20, 42, 96), (7, 13, 40), (156, 202, 240)),
    "air": ((92, 78, 26), (28, 24, 9), (246, 228, 150)),
    "earth": ((22, 78, 46), (7, 27, 17), (156, 216, 172)),
    "major": ((60, 30, 96), (17, 9, 34), GOLD_HI),
}

_COURT_ABBR = {"knight": "Kn", "queen": "Q", "prince": "Pr", "princess": "Ps"}


# --------------------------------------------------------------------------
# low-level helpers
# --------------------------------------------------------------------------


def _font(size: int):
    for name in ("DejaVuSerif.ttf", "DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _rng(card: Card):
    """Deterministic per-card RNG (star-dust), independent of PYTHONHASHSEED."""
    import hashlib
    import random

    seed = int.from_bytes(hashlib.sha256(card.id.encode()).digest()[:4], "big")
    return random.Random(seed)


def _palette(card: Card):
    return _PALETTE["major"] if card.kind == "major" else _PALETTE[card.element]


def _gradient(w: int, h: int, top, bottom) -> Image.Image:
    img = Image.new("RGB", (w, h), top)
    d = ImageDraw.Draw(img)
    for y in range(h):
        f = y / max(1, h - 1)
        d.line(
            [(0, y), (w, y)],
            fill=tuple(int(top[i] + (bottom[i] - top[i]) * f) for i in range(3)),
        )
    return img


def _vignette(w: int, h: int) -> Image.Image:
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse([-w * 0.2, -h * 0.15, w * 1.2, h * 1.15], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(w * 0.10))
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    layer.putalpha(Image.eval(mask, lambda v: int((255 - v) * 0.72)))
    return layer


def _starfield(w: int, h: int, rng) -> Image.Image:
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(70):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        r = rng.uniform(w * 0.001, w * 0.004)
        a = rng.randint(30, 120)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 244, 214, a))
    return layer


def _glow(w: int, h: int, cx, cy, r, color, alpha) -> Image.Image:
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, alpha))
    return layer.filter(ImageFilter.GaussianBlur(r * 0.5))


def _centered(d, cx, y, text, font, fill):
    d.text((cx, y), text, font=font, fill=fill, anchor="ma")


def _wrap(d, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        trial = f"{cur} {wd}".strip()
        if d.textbbox((0, 0), trial, font=font)[2] <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


# --------------------------------------------------------------------------
# suit glyphs (drawn within a bounding circle of radius r at cx, cy)
# --------------------------------------------------------------------------


def _wand(d, cx, cy, r, col, lw):
    top = cy - r * 0.62
    d.line([(cx, cy + r), (cx, top)], fill=col, width=lw)
    # lotus finial: three petals
    for dx in (-1.0, 0.0, 1.0):
        px = cx + dx * r * 0.34
        pw, ph = r * 0.2, r * 0.42
        py = top - r * 0.02
        d.ellipse([px - pw, py - ph, px + pw, py + r * 0.05], outline=col, width=max(2, lw // 2))
    d.ellipse([cx - r * 0.1, cy + r * 0.86, cx + r * 0.1, cy + r * 1.06], fill=col)


def _cup(d, cx, cy, r, col, lw):
    rw = r * 0.62
    rim = cy - r * 0.62
    d.ellipse([cx - rw, rim - r * 0.12, cx + rw, rim + r * 0.12], outline=col, width=lw)
    d.line([(cx - rw, rim), (cx - r * 0.14, cy + r * 0.12)], fill=col, width=lw)
    d.line([(cx + rw, rim), (cx + r * 0.14, cy + r * 0.12)], fill=col, width=lw)
    d.arc([cx - r * 0.5, cy - r * 0.25, cx + r * 0.5, cy + r * 0.3], 5, 175, fill=col, width=lw)
    d.line([(cx, cy + r * 0.22), (cx, cy + r * 0.66)], fill=col, width=lw)
    d.ellipse([cx - r * 0.44, cy + r * 0.66, cx + r * 0.44, cy + r * 0.86], outline=col, width=lw)


def _sword(d, cx, cy, r, col, lw):
    d.polygon(
        [(cx, cy - r), (cx + r * 0.16, cy + r * 0.34), (cx - r * 0.16, cy + r * 0.34)],
        outline=col,
        width=lw,
    )
    d.line([(cx - r * 0.5, cy + r * 0.36), (cx + r * 0.5, cy + r * 0.36)], fill=col, width=lw)
    d.line([(cx, cy + r * 0.36), (cx, cy + r * 0.82)], fill=col, width=lw)
    d.ellipse([cx - r * 0.13, cy + r * 0.82, cx + r * 0.13, cy + r * 1.08], outline=col, width=lw)


def _disk(d, cx, cy, r, col, lw):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=lw)
    d.ellipse(
        [cx - r * 0.66, cy - r * 0.66, cx + r * 0.66, cy + r * 0.66],
        outline=col,
        width=max(2, lw // 2),
    )
    for i in range(8):
        a = i * math.pi / 4
        x0, y0 = cx + r * 0.7 * math.cos(a), cy + r * 0.7 * math.sin(a)
        x1, y1 = cx + r * 0.95 * math.cos(a), cy + r * 0.95 * math.sin(a)
        d.line([(x0, y0), (x1, y1)], fill=col, width=max(2, lw // 2))
    _star(d, cx, cy, r * 0.42, r * 0.17, col, lw=max(2, lw // 2), fill=None)


_SUIT_GLYPH = {"wands": _wand, "cups": _cup, "swords": _sword, "disks": _disk}


# --------------------------------------------------------------------------
# shared primitive emblems
# --------------------------------------------------------------------------


def _star_points(cx, cy, outer, inner, n=5, rot=-math.pi / 2):
    pts = []
    for i in range(n):
        ao = rot + i * 2 * math.pi / n
        ai = ao + math.pi / n
        pts.append((cx + outer * math.cos(ao), cy + outer * math.sin(ao)))
        pts.append((cx + inner * math.cos(ai), cy + inner * math.sin(ai)))
    return pts


def _star(d, cx, cy, outer, inner, col, lw, fill=None, n=5, rot=-math.pi / 2):
    d.polygon(_star_points(cx, cy, outer, inner, n, rot), outline=col, width=lw, fill=fill)


def _sun(d, cx, cy, r, col, lw):
    for i in range(12):
        a = i * math.pi / 6
        d.line(
            [
                (cx + r * 0.72 * math.cos(a), cy + r * 0.72 * math.sin(a)),
                (cx + r * 1.05 * math.cos(a), cy + r * 1.05 * math.sin(a)),
            ],
            fill=col,
            width=lw,
        )
    d.ellipse([cx - r * 0.6, cy - r * 0.6, cx + r * 0.6, cy + r * 0.6], outline=col, width=lw)


def _crescent(d, cx, cy, r, col, lw):
    d.arc([cx - r, cy - r, cx + r, cy + r], 55, 305, fill=col, width=lw)
    d.arc([cx - r * 0.35, cy - r, cx + r * 1.25, cy + r], 70, 290, fill=col, width=lw)


def _wheel(d, cx, cy, r, col, lw, spokes=8):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=lw)
    d.ellipse([cx - r * 0.28, cy - r * 0.28, cx + r * 0.28, cy + r * 0.28], outline=col, width=lw)
    for i in range(spokes):
        a = i * 2 * math.pi / spokes
        d.line(
            [
                (cx + r * 0.28 * math.cos(a), cy + r * 0.28 * math.sin(a)),
                (cx + r * math.cos(a), cy + r * math.sin(a)),
            ],
            fill=col,
            width=max(2, lw // 2),
        )


def _crown(d, cx, cy, r, col, lw):
    base = cy + r * 0.35
    pts = [
        (cx - r, base),
        (cx - r, base - r * 0.5),
        (cx - r * 0.5, base - r * 0.15),
        (cx, base - r * 0.75),
        (cx + r * 0.5, base - r * 0.15),
        (cx + r, base - r * 0.5),
        (cx + r, base),
    ]
    d.line([*pts, pts[0]], fill=col, width=lw, joint="curve")
    for px in (cx - r, cx, cx + r):
        d.ellipse([px - r * 0.12, base - r * 0.88, px + r * 0.12, base - r * 0.64], fill=col)


def _hexagram(d, cx, cy, r, col, lw):
    _star(d, cx, cy, r, r * 0.58, col, lw, n=3, rot=-math.pi / 2)
    _star(d, cx, cy, r, r * 0.58, col, lw, n=3, rot=math.pi / 2)


def _eye(d, cx, cy, r, col, lw):
    d.arc([cx - r, cy - r * 0.7, cx + r, cy + r * 0.7], 20, 160, fill=col, width=lw)
    d.arc([cx - r, cy - r * 0.7, cx + r, cy + r * 0.7], 200, 340, fill=col, width=lw)
    d.ellipse([cx - r * 0.3, cy - r * 0.3, cx + r * 0.3, cy + r * 0.3], outline=col, width=lw)
    d.ellipse([cx - r * 0.1, cy - r * 0.1, cx + r * 0.1, cy + r * 0.1], fill=col)
    for i in range(7):
        a = math.pi * (0.15 + 0.7 * i / 6)
        d.line(
            [
                (cx + r * 1.05 * math.cos(a), cy - r * 0.9 - r * 0.1),
                (cx + r * 1.3 * math.cos(a), cy - r * 1.15),
            ],
            fill=col,
            width=max(2, lw // 2),
        )


def _tower(d, cx, cy, r, col, lw):
    d.rectangle([cx - r * 0.42, cy - r * 0.4, cx + r * 0.42, cy + r], outline=col, width=lw)
    for bx in (-0.42, -0.14, 0.14):
        d.rectangle(
            [cx + bx * r, cy - r * 0.62, cx + (bx + 0.28) * r, cy - r * 0.4],
            outline=col,
            width=max(2, lw // 2),
        )
    # lightning
    d.line(
        [
            (cx + r * 0.1, cy - r * 1.15),
            (cx - r * 0.16, cy - r * 0.45),
            (cx + r * 0.12, cy - r * 0.5),
            (cx - r * 0.1, cy + r * 0.1),
        ],
        fill=col,
        width=lw,
        joint="curve",
    )


def _scales(d, cx, cy, r, col, lw):
    d.line([(cx, cy - r), (cx, cy + r * 0.7)], fill=col, width=lw)
    d.line([(cx - r, cy - r * 0.55), (cx + r, cy - r * 0.55)], fill=col, width=lw)
    for sx in (-1, 1):
        ex = cx + sx * r
        pan_y = cy + r * 0.12
        d.line([(ex, cy - r * 0.55), (ex - r * 0.3, pan_y)], fill=col, width=max(2, lw // 2))
        d.line([(ex, cy - r * 0.55), (ex + r * 0.3, pan_y)], fill=col, width=max(2, lw // 2))
        d.arc(
            [ex - r * 0.32, pan_y - r * 0.14, ex + r * 0.32, pan_y + r * 0.24],
            0,
            180,
            fill=col,
            width=lw,
        )
    d.polygon(
        [(cx, cy + r * 0.7), (cx - r * 0.3, cy + r), (cx + r * 0.3, cy + r)], outline=col, width=lw
    )


def _lantern(d, cx, cy, r, col, lw):
    d.arc([cx - r * 0.4, cy - r, cx + r * 0.4, cy - r * 0.5], 180, 360, fill=col, width=lw)
    d.rectangle([cx - r * 0.45, cy - r * 0.55, cx + r * 0.45, cy + r * 0.7], outline=col, width=lw)
    d.line(
        [(cx - r * 0.45, cy - r * 0.2), (cx + r * 0.45, cy - r * 0.2)],
        fill=col,
        width=max(2, lw // 2),
    )
    d.line(
        [(cx - r * 0.45, cy + r * 0.35), (cx + r * 0.45, cy + r * 0.35)],
        fill=col,
        width=max(2, lw // 2),
    )
    _star(d, cx, cy + r * 0.08, r * 0.26, r * 0.1, GOLD_HI, lw=max(2, lw // 2), fill=GOLD_HI)


def _scythe(d, cx, cy, r, col, lw):
    d.line([(cx + r * 0.35, cy - r), (cx + r * 0.05, cy + r)], fill=col, width=lw)
    d.arc([cx - r, cy - r * 1.1, cx + r * 0.7, cy + r * 0.2], 200, 340, fill=col, width=lw)


def _keys(d, cx, cy, r, col, lw):
    for sx in (-0.28, 0.28):
        x = cx + sx * r
        d.ellipse([x - r * 0.22, cy - r, x + r * 0.22, cy - r * 0.56], outline=col, width=lw)
        d.line([(x, cy - r * 0.56), (x, cy + r)], fill=col, width=lw)
        d.line([(x, cy + r * 0.7), (x + r * 0.22, cy + r * 0.7)], fill=col, width=max(2, lw // 2))
        d.line([(x, cy + r), (x + r * 0.22, cy + r)], fill=col, width=max(2, lw // 2))


def _rings(d, cx, cy, r, col, lw):
    d.ellipse([cx - r, cy - r * 0.7, cx, cy + r * 0.7], outline=col, width=lw)
    d.ellipse([cx, cy - r * 0.7, cx + r, cy + r * 0.7], outline=col, width=lw)


def _rose(d, cx, cy, r, col, lw):
    for i in range(6):
        a = i * math.pi / 3
        px, py = cx + r * 0.45 * math.cos(a), cy + r * 0.45 * math.sin(a)
        d.ellipse(
            [px - r * 0.4, py - r * 0.4, px + r * 0.4, py + r * 0.4],
            outline=col,
            width=max(2, lw // 2),
        )
    d.ellipse([cx - r * 0.3, cy - r * 0.3, cx + r * 0.3, cy + r * 0.3], outline=col, width=lw)


def _horns(d, cx, cy, r, col, lw):
    _star(d, cx, cy - r * 0.1, r, r * 0.42, col, lw, n=5, rot=math.pi / 2)  # inverted pentagram


def _ankh(d, cx, cy, r, col, lw):
    d.ellipse([cx - r * 0.4, cy - r, cx + r * 0.4, cy - r * 0.1], outline=col, width=lw)
    d.line([(cx, cy - r * 0.1), (cx, cy + r)], fill=col, width=lw)
    d.line([(cx - r * 0.55, cy + r * 0.2), (cx + r * 0.55, cy + r * 0.2)], fill=col, width=lw)


def _flame(d, cx, cy, r, col, lw):
    d.polygon(
        [
            (cx, cy - r),
            (cx + r * 0.55, cy + r * 0.2),
            (cx + r * 0.3, cy + r),
            (cx - r * 0.3, cy + r),
            (cx - r * 0.55, cy + r * 0.2),
        ],
        outline=col,
        width=lw,
    )
    d.line([(cx, cy - r * 0.3), (cx - r * 0.15, cy + r * 0.6)], fill=col, width=max(2, lw // 2))


def _winged_rod(d, cx, cy, r, col, lw):
    d.line([(cx, cy - r), (cx, cy + r)], fill=col, width=lw)
    d.ellipse([cx - r * 0.16, cy - r * 1.12, cx + r * 0.16, cy - r * 0.8], fill=col)
    for s in (-1, 1):
        for k in range(3):
            yy = cy - r * 0.55 + k * r * 0.3
            d.line([(cx, yy), (cx + s * r * 0.9, yy - r * 0.22)], fill=col, width=max(2, lw // 2))


def _hanged(d, cx, cy, r, col, lw):
    d.line([(cx - r, cy - r), (cx + r, cy - r)], fill=col, width=lw)
    d.line([(cx + r * 0.2, cy - r), (cx + r * 0.2, cy - r * 0.5)], fill=col, width=lw)
    d.ellipse([cx + r * 0.02, cy - r * 0.5, cx + r * 0.38, cy - r * 0.14], outline=col, width=lw)
    d.polygon(
        [
            (cx + r * 0.2, cy - r * 0.14),
            (cx - r * 0.35, cy + r * 0.6),
            (cx + r * 0.55, cy + r * 0.35),
        ],
        outline=col,
        width=lw,
    )


def _wreath(d, cx, cy, r, col, lw):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=lw)
    for i in range(16):
        a = i * math.pi / 8
        d.arc(
            [
                cx + (r - r * 0.16) * math.cos(a) - r * 0.16,
                cy + (r - r * 0.16) * math.sin(a) - r * 0.16,
                cx + (r - r * 0.16) * math.cos(a) + r * 0.16,
                cy + (r - r * 0.16) * math.sin(a) + r * 0.16,
            ],
            0,
            360,
            fill=col,
            width=max(1, lw // 3),
        )
    _star(d, cx, cy, r * 0.34, r * 0.14, GOLD_HI, lw=max(2, lw // 2), fill=GOLD_HI)


def _moon_scene(d, cx, cy, r, col, lw):
    _crescent(d, cx, cy - r * 0.15, r * 0.8, col, lw)
    for dx in (-0.5, 0.0, 0.5):
        d.line(
            [(cx + dx * r, cy + r * 0.5), (cx + dx * r, cy + r)],
            fill=col,
            width=max(2, lw // 2),
        )


def _starburst(d, cx, cy, r, col, lw):
    for i in range(8):
        a = i * math.pi / 4
        ln = r if i % 2 == 0 else r * 0.6
        d.line([(cx, cy), (cx + ln * math.cos(a), cy + ln * math.sin(a))], fill=col, width=lw)
    d.ellipse([cx - r * 0.14, cy - r * 0.14, cx + r * 0.14, cy + r * 0.14], fill=col)


def _big_star(d, cx, cy, r, col, lw):
    _star(d, cx, cy, r, r * 0.42, col, lw, n=7, rot=-math.pi / 2)
    _star(d, cx, cy, r * 0.44, r * 0.18, GOLD_HI, lw=max(2, lw // 2), fill=None, n=7)


# major number -> emblem drawing function
_MAJOR_EMBLEMS = {
    0: _starburst,
    1: _winged_rod,
    2: _crescent,
    3: _rose,
    4: _crown,
    5: _keys,
    6: _rings,
    7: lambda d, cx, cy, r, c, lw: _wheel(d, cx, cy, r, c, lw, spokes=6),
    8: _scales,
    9: _lantern,
    10: lambda d, cx, cy, r, c, lw: _wheel(d, cx, cy, r, c, lw, spokes=8),
    11: _flame,
    12: _hanged,
    13: _scythe,
    14: _hexagram,
    15: _horns,
    16: _tower,
    17: _big_star,
    18: _moon_scene,
    19: _sun,
    20: _eye,
    21: _wreath,
}

# court rank -> a small emblem drawn above the medallion
_COURT_MARK = {
    "knight": lambda d, cx, cy, r, c, lw: d.polygon(
        [(cx - r, cy + r * 0.4), (cx, cy - r * 0.7), (cx + r, cy + r * 0.4)], outline=c, width=lw
    ),
    "queen": _crown,
    "prince": lambda d, cx, cy, r, c, lw: _star(d, cx, cy, r * 0.9, r * 0.4, c, lw, n=5),
    "princess": lambda d, cx, cy, r, c, lw: d.arc(
        [cx - r, cy - r * 0.5, cx + r, cy + r], 190, 350, fill=c, width=lw
    ),
}


# --------------------------------------------------------------------------
# pip layouts
# --------------------------------------------------------------------------

_PIP_LAYOUTS = {
    1: [(0.5, 0.5)],
    2: [(0.5, 0.24), (0.5, 0.76)],
    3: [(0.5, 0.18), (0.5, 0.5), (0.5, 0.82)],
    4: [(0.32, 0.26), (0.68, 0.26), (0.32, 0.74), (0.68, 0.74)],
    5: [(0.3, 0.22), (0.7, 0.22), (0.5, 0.5), (0.3, 0.78), (0.7, 0.78)],
    6: [(0.32, 0.18), (0.68, 0.18), (0.32, 0.5), (0.68, 0.5), (0.32, 0.82), (0.68, 0.82)],
    7: [
        (0.32, 0.16),
        (0.68, 0.16),
        (0.5, 0.33),
        (0.32, 0.52),
        (0.68, 0.52),
        (0.32, 0.85),
        (0.68, 0.85),
    ],
    8: [
        (0.32, 0.14),
        (0.68, 0.14),
        (0.32, 0.38),
        (0.68, 0.38),
        (0.32, 0.62),
        (0.68, 0.62),
        (0.32, 0.86),
        (0.68, 0.86),
    ],
    9: [
        (0.32, 0.14),
        (0.68, 0.14),
        (0.32, 0.38),
        (0.68, 0.38),
        (0.5, 0.5),
        (0.32, 0.62),
        (0.68, 0.62),
        (0.32, 0.86),
        (0.68, 0.86),
    ],
    10: [
        (0.32, 0.13),
        (0.68, 0.13),
        (0.5, 0.3),
        (0.32, 0.4),
        (0.68, 0.4),
        (0.32, 0.62),
        (0.68, 0.62),
        (0.5, 0.72),
        (0.32, 0.88),
        (0.68, 0.88),
    ],
}
_PIP_SCALE = {1: 1.0, 2: 0.9, 3: 0.85, 4: 0.8, 5: 0.72, 6: 0.7, 7: 0.6, 8: 0.56, 9: 0.54, 10: 0.5}


# --------------------------------------------------------------------------
# card composition
# --------------------------------------------------------------------------


def _draw_frame(d, w, h, accent):
    r = w * 0.06
    d.rounded_rectangle(
        [w * 0.03, h * 0.02, w * 0.97, h * 0.98],
        radius=r,
        outline=accent,
        width=max(3, int(w * 0.012)),
    )
    d.rounded_rectangle(
        [w * 0.055, h * 0.035, w * 0.945, h * 0.965],
        radius=r * 0.7,
        outline=accent,
        width=max(2, int(w * 0.004)),
    )
    for cx, cy in [
        (w * 0.08, h * 0.05),
        (w * 0.92, h * 0.05),
        (w * 0.08, h * 0.95),
        (w * 0.92, h * 0.95),
    ]:
        _star(d, cx, cy, w * 0.02, w * 0.008, accent, lw=max(2, int(w * 0.004)), fill=accent, n=4)


def render_card(card: Card, size=(CARD_W, CARD_H)) -> Image.Image:
    """Original vector art for one card at ``size``."""
    ow, oh = size
    w, h = ow * _SS, oh * _SS
    top, bottom, sym = _palette(card)
    accent = GOLD

    img = _gradient(w, h, top, bottom).convert("RGBA")
    img = Image.alpha_composite(img, _starfield(w, h, _rng(card)))

    cx = w / 2
    emblem_cy = h * 0.4
    emblem_r = w * 0.2

    # soft glow behind the focal art for aces / courts / majors
    if (
        card.kind == "major"
        or (card.kind == "minor" and not isinstance(card.rank, int))
        or card.rank == 1
    ):
        img = Image.alpha_composite(img, _glow(w, h, cx, emblem_cy, emblem_r * 1.5, sym, 90))

    d = ImageDraw.Draw(img)
    lw = max(3, int(w * 0.011))

    # --- emblem -----------------------------------------------------------
    if card.kind == "major":
        _MAJOR_EMBLEMS[card.number](d, cx, emblem_cy, emblem_r, sym, lw)
    elif isinstance(card.rank, int):
        glyph = _SUIT_GLYPH[card.suit]
        if card.rank == 1:
            glyph(d, cx, emblem_cy, emblem_r, sym, lw)
        else:
            area = (w * 0.16, h * 0.14, w * 0.84, h * 0.66)
            base_r = w * 0.14 * _PIP_SCALE[card.rank]
            for fx, fy in _PIP_LAYOUTS[card.rank]:
                px = area[0] + fx * (area[2] - area[0])
                py = area[1] + fy * (area[3] - area[1])
                glyph(d, px, py, base_r, sym, max(2, int(base_r * 0.14)))
    else:
        # court: medallion + suit glyph + rank mark above
        d.ellipse(
            [cx - emblem_r, emblem_cy - emblem_r, cx + emblem_r, emblem_cy + emblem_r],
            outline=accent,
            width=lw,
        )
        _SUIT_GLYPH[card.suit](d, cx, emblem_cy + emblem_r * 0.08, emblem_r * 0.6, sym, lw)
        _COURT_MARK[card.rank](
            d, cx, emblem_cy - emblem_r * 1.28, emblem_r * 0.34, accent, max(2, lw // 2)
        )

    # --- top marker roundel ----------------------------------------------
    if card.kind == "major":
        marker = card.roman
    elif isinstance(card.rank, int):
        marker = "A" if card.rank == 1 else str(card.rank)
    else:
        marker = _COURT_ABBR[card.rank]
    mfont = _font(int(w * 0.09))
    d.ellipse(
        [cx - w * 0.09, h * 0.055, cx + w * 0.09, h * 0.055 + w * 0.18],
        outline=accent,
        width=max(2, lw // 2),
    )
    _centered(d, cx, h * 0.055 + w * 0.045, marker, mfont, GOLD_HI)

    # --- title band -------------------------------------------------------
    d.line([(w * 0.16, h * 0.74), (w * 0.84, h * 0.74)], fill=accent, width=max(2, lw // 2))
    name_font = _font(int(w * 0.072))
    y = h * 0.77
    for line in _wrap(d, card.name, name_font, w * 0.72):
        _centered(d, cx, y, line, name_font, (248, 246, 240))
        y += w * 0.085
    if card.title:
        y += h * 0.005
        for line in _wrap(d, card.title, _font(int(w * 0.05)), w * 0.72):
            _centered(d, cx, y, line, _font(int(w * 0.05)), accent)
            y += w * 0.06

    _draw_frame(d, w, h, accent)
    img = Image.alpha_composite(img, _vignette(w, h))
    return img.convert("RGB").resize((ow, oh), Image.LANCZOS)


def load_or_render(card_id: str) -> Image.Image:
    card = get_card(card_id)
    path = ASSET_DIR / f"{card_id}.png"
    if path.exists():
        try:
            return Image.open(path).convert("RGB").resize((CARD_W, CARD_H))
        except OSError:
            pass
    return render_card(card)


def compose(card_ids: list[str]) -> bytes:
    """Tile the cards into a single PNG (bytes) for sending to Telegram."""
    n = len(card_ids)
    width = _MARGIN * 2 + n * CARD_W + (n - 1) * _GAP
    height = _MARGIN * 2 + CARD_H
    canvas = Image.new("RGB", (width, height), (16, 12, 22))
    x = _MARGIN
    for cid in card_ids:
        canvas.paste(load_or_render(cid), (x, _MARGIN))
        x += CARD_W + _GAP
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()
