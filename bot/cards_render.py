"""Render Thoth cards to images (Pillow).

Thin IO/presentation layer — not unit-tested. A single-card procedural renderer
(:func:`render_card`) is the source of the bundled assets (see
``tools/generate_cards.py``) and the runtime fallback when an asset PNG is
missing. :func:`compose` tiles the drawn cards into one image for Telegram.

Swap the art for AI-generated Thoth cards by replacing the PNGs in
``assets/cards/`` — the ids/filenames and this module's interface stay the same.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .deck import Card, get_card

ASSET_DIR = Path(__file__).resolve().parent.parent / "assets" / "cards"

CARD_W, CARD_H = 360, 600
_MARGIN = 24
_GAP = 20

# Element / arcana palettes: (top gradient, bottom gradient, accent).
_PALETTE = {
    "fire": ((120, 20, 20), (40, 8, 8), (245, 180, 90)),
    "water": ((20, 45, 110), (8, 16, 45), (140, 190, 245)),
    "air": ((120, 100, 20), (45, 38, 8), (245, 230, 140)),
    "earth": ((20, 80, 45), (8, 30, 18), (150, 220, 170)),
    "major": ((70, 30, 100), (24, 10, 40), (240, 210, 130)),
}

_COURT_ABBR = {"knight": "Kn", "queen": "Q", "prince": "Pr", "princess": "Ps"}


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _palette_for(card: Card):
    return _PALETTE["major"] if card.kind == "major" else _PALETTE[card.element]


def _gradient(size, top, bottom) -> Image.Image:
    w, h = size
    base = Image.new("RGB", size, top)
    draw = ImageDraw.Draw(base)
    for y in range(h):
        f = y / max(1, h - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * f) for i in range(3))
        draw.line([(0, y), (w, y)], fill=color)
    return base


def _centered(draw, cx, y, text, font, fill):
    box = draw.textbbox((0, 0), text, font=font)
    draw.text((cx - (box[2] - box[0]) / 2, y), text, font=font, fill=fill)


def _draw_symbol(draw, card: Card, cx: float, cy: float, r: float, accent) -> None:
    """Draw the central element/arcana emblem as a vector shape (robust across
    fonts): triangle up=fire, down=water, diamond=air, square=earth, star=major."""
    w = 5
    if card.kind == "major":
        pts = []
        import math

        for i in range(5):
            a_out = -math.pi / 2 + i * 2 * math.pi / 5
            a_in = a_out + math.pi / 5
            pts.append((cx + r * math.cos(a_out), cy + r * math.sin(a_out)))
            pts.append((cx + r * 0.4 * math.cos(a_in), cy + r * 0.4 * math.sin(a_in)))
        draw.polygon(pts, outline=accent, width=w)
        return
    if card.element == "fire":
        pts = [(cx, cy - r), (cx - r * 0.87, cy + r * 0.5), (cx + r * 0.87, cy + r * 0.5)]
    elif card.element == "water":
        pts = [(cx, cy + r), (cx - r * 0.87, cy - r * 0.5), (cx + r * 0.87, cy - r * 0.5)]
    elif card.element == "air":
        pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    else:  # earth
        s = r * 0.8
        pts = [(cx - s, cy - s), (cx + s, cy - s), (cx + s, cy + s), (cx - s, cy + s)]
    draw.polygon(pts, outline=accent, width=w)


def _wrap(draw, text, font, max_w) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textbbox((0, 0), trial, font=font)[2] <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_card(card: Card, size=(CARD_W, CARD_H)) -> Image.Image:
    """Procedural art for one card: gradient by element, rank/roman, a central
    glyph, and the English name + Thoth title."""
    w, h = size
    top, bottom, accent = _palette_for(card)
    img = _gradient(size, top, bottom)
    draw = ImageDraw.Draw(img)

    # Frame.
    draw.rectangle([6, 6, w - 7, h - 7], outline=accent, width=3)
    draw.rectangle([14, 14, w - 15, h - 15], outline=accent, width=1)

    cx = w / 2

    # Top marker: roman (major) / rank number (pip) / court abbreviation.
    if card.kind == "major":
        marker = card.roman
    elif isinstance(card.rank, int):
        marker = "A" if card.rank == 1 else str(card.rank)
    else:
        marker = _COURT_ABBR[card.rank]
    _centered(draw, cx, 34, marker, _font(40), accent)

    # Central emblem (vector, so it never renders as a missing-glyph box).
    _draw_symbol(draw, card, cx, h * 0.40, 90, accent)

    # Name (wrapped) + title near the bottom.
    name_font = _font(30)
    lines = _wrap(draw, card.name, name_font, w - 60)
    y = h - 150
    for line in lines:
        _centered(draw, cx, y, line, name_font, (245, 245, 245))
        y += 36
    if card.title:
        y += 4
        for line in _wrap(draw, card.title, _font(20), w - 60):
            _centered(draw, cx, y, line, _font(20), accent)
            y += 26
    return img


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
    canvas = Image.new("RGB", (width, height), (18, 14, 24))
    x = _MARGIN
    for cid in card_ids:
        canvas.paste(load_or_render(cid), (x, _MARGIN))
        x += CARD_W + _GAP
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()
