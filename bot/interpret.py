"""Reading generation via the Claude API.

The prompt-building functions (``build_*``) are pure and unit-tested — no
network. The ``Interpreter`` class is the thin IO boundary that calls the
Anthropic SDK; it is not unit-tested.

Product rule baked into the system prompt: readings explain the querent's
**current disposition** and are dry and explanatory — *no fortune-telling* —
except the dedicated "future" reading, which is the one paid exception.
"""

from __future__ import annotations

from .card_names import card_name
from .deck import Card, get_card

# What language Claude should answer in, phrased for the prompt.
_LANG_INSTRUCTION = {
    "ru": "русском",
    "uk": "українською",
    "en": "English",
}

_SYSTEM = (
    "You are an experienced reader of the Thoth Tarot (Crowley–Harris deck). "
    "You interpret a spread as a picture of the querent's CURRENT disposition — "
    "the forces, tensions and standing of the situation right now. "
    "You do NOT predict the future and you do NOT give advice unless asked; you "
    "explain what the cards describe, soberly and concretely, grounding each "
    "reading in the Thoth meaning of the specific cards drawn. "
    "Write in {lang}. Refer to the cards by their names in that language. "
    "Answer directly with the interpretation — no preamble, no thinking aloud, "
    "no bullet-point disclaimers. Keep it to a few tight paragraphs."
)

_FUTURE_SYSTEM = (
    "You are an experienced reader of the Thoth Tarot (Crowley–Harris deck). "
    "This is the one reading where the querent has explicitly asked you to look "
    "AHEAD: given the spread already laid, describe the likely trajectory and "
    "where these forces are heading. Stay grounded in the Thoth meanings of the "
    "cards; be concrete, not vague or grandiose. "
    "Write in {lang}. Answer directly, no preamble."
)


def _card_brief(card: Card, lang: str) -> str:
    """One line describing a card for the model, grounding it in Thoth meaning."""
    local = card_name(card, lang)
    if card.kind == "major":
        return f"- {local} (Atu {card.roman}, «{card.name}»), Major Arcana"
    parts = [f"- {local} («{card.name}»)", f"suit of {card.suit} / {card.element}"]
    if card.title:
        parts.append(f"Thoth title: «{card.title}»")
    return ", ".join(parts)


def _cards_block(card_ids: list[str], lang: str) -> str:
    return "\n".join(_card_brief(get_card(cid), lang) for cid in card_ids)


def system_prompt(lang: str) -> str:
    return _SYSTEM.format(lang=_LANG_INSTRUCTION.get(lang, "English"))


def future_system_prompt(lang: str) -> str:
    return _FUTURE_SYSTEM.format(lang=_LANG_INSTRUCTION.get(lang, "English"))


def build_daily_user(card_ids: list[str], lang: str) -> str:
    return (
        "Three cards were drawn for the querent's disposition today:\n"
        f"{_cards_block(card_ids, lang)}\n\n"
        "Interpret this three-card spread as the querent's current disposition."
    )


def build_context_user(card_ids: list[str], situation: str, lang: str) -> str:
    return (
        "The querent describes this situation:\n"
        f"«{situation.strip()}»\n\n"
        "Three cards were drawn to read that situation:\n"
        f"{_cards_block(card_ids, lang)}\n\n"
        "Interpret this three-card spread as the current disposition of the "
        "described situation specifically."
    )


def build_future_user(card_ids: list[str], base_interpretation: str, lang: str) -> str:
    return (
        "The spread already laid for the querent's disposition:\n"
        f"{_cards_block(card_ids, lang)}\n\n"
        "Its reading of the current disposition was:\n"
        f"«{base_interpretation.strip()}»\n\n"
        "Now look ahead: describe where these forces are heading."
    )


def build_extra_user(
    base_card_ids: list[str],
    base_interpretation: str,
    extra_card_ids: list[str],
    lang: str,
) -> str:
    return (
        "An existing spread for the querent's disposition:\n"
        f"{_cards_block(base_card_ids, lang)}\n\n"
        "Its reading was:\n"
        f"«{base_interpretation.strip()}»\n\n"
        f"{len(extra_card_ids)} clarifying cards have now been added:\n"
        f"{_cards_block(extra_card_ids, lang)}\n\n"
        "Interpret ONLY the clarifying cards, within the context of the existing "
        "spread — how they refine, deepen or qualify its reading of the current "
        "disposition. Do not re-interpret the original cards from scratch."
    )


class Interpreter:
    """Thin wrapper over the async Anthropic SDK."""

    def __init__(self, model: str, max_tokens: int = 1200):
        # Imported lazily so the pure prompt builders (and their tests) don't
        # require the anthropic package or an API key.
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic()  # reads ANTHROPIC_API_KEY from env
        self._model = model
        self._max_tokens = max_tokens

    async def _complete(self, system: str, user: str) -> str:
        resp = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in resp.content if b.type == "text").strip()

    async def daily(self, card_ids: list[str], lang: str) -> str:
        return await self._complete(system_prompt(lang), build_daily_user(card_ids, lang))

    async def context(self, card_ids: list[str], situation: str, lang: str) -> str:
        return await self._complete(
            system_prompt(lang), build_context_user(card_ids, situation, lang)
        )

    async def future(self, card_ids: list[str], base_interpretation: str, lang: str) -> str:
        return await self._complete(
            future_system_prompt(lang),
            build_future_user(card_ids, base_interpretation, lang),
        )

    async def extra(
        self,
        base_card_ids: list[str],
        base_interpretation: str,
        extra_card_ids: list[str],
        lang: str,
    ) -> str:
        return await self._complete(
            system_prompt(lang),
            build_extra_user(base_card_ids, base_interpretation, extra_card_ids, lang),
        )
