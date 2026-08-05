"""Reading generation via the Claude API.

The prompt-building functions (``build_*``) are pure and unit-tested — no
network. The ``Interpreter`` class is the thin IO boundary that calls the
Anthropic SDK; it is not unit-tested.

Product rule baked into the system prompt: readings explain the querent's
**current disposition** and are dry and explanatory — *no fortune-telling* —
except the dedicated "future" reading, which is the one paid exception.
"""

from __future__ import annotations

from . import style as style_mod
from .card_names import card_name
from .deck import Card, get_card

# What language Claude should answer in, phrased for the prompt.
_LANG_INSTRUCTION = {
    "ru": "русском",
    "uk": "українською",
    "en": "English",
}

_BASE = (
    "You are an experienced reader of the Thoth Tarot (Crowley–Harris deck). "
    "You interpret a spread as a picture of the querent's CURRENT disposition — "
    "the forces, tensions and standing of the situation right now. "
    "You do NOT predict the future and you do NOT give advice unless asked; you "
    "explain what the cards describe, soberly and concretely, grounding each "
    "reading in the Thoth meaning of the specific cards drawn. "
    "Write in {lang}. Refer to the cards by their names in that language. "
    "Answer directly with the interpretation — no preamble, no thinking aloud, "
    "no bullet-point disclaimers. "
)

# Default voice: short. The querent can pay/tap to expand, so the first read
# must be tight — a taste, not the whole essay.
_BRIEF = (
    "Be BRIEF: 3–5 sentences, one short paragraph, under 600 characters. "
    "Name the cards and say what they describe together. No card-by-card "
    "walkthrough, no filler, no restating the question."
)

_DEEP = (
    "This is the EXPANDED reading the querent asked for after a short one. Go "
    "deep: walk through each card's contribution, how they interact and qualify "
    "one another, the tensions and the through-line. Four to six paragraphs. Do "
    "not simply repeat the short reading — build on it with detail it omitted."
)

# Added only when the querent actually has a history (see bot/memory.py). The
# leash is deliberate: an invented "last week the Tower came up" would be worse
# than no memory at all, and a history recap would eat the whole brief reading.
_MEMORY_RULE = (
    " The querent's own earlier readings are listed for you. Use them ONLY where they bear on "
    "today's cards: if a card returns or a question continues, note it in ONE short clause "
    "saying when it last came up, then read today's spread. Never mention a reading, card or "
    "date that is not in that list, never guess at what an earlier reading said, and do not "
    "recap the history for its own sake."
)

# The querent's chosen voice (bot/style.py), appended last so it governs the
# tone. It governs *only* the tone: the rules above it — current disposition,
# no prediction, brevity — hold in every style. FORTUNE appends nothing, so the
# default persona's prompt stays exactly what it always was.
_STYLE_VOICES = {
    style_mod.PSY: (
        " VOICE — psychologist: read the spread as projective material. Name the inner "
        "conflict, the motive, the defence and the need under the situation in plain "
        "psychological language (ambivalence, avoidance, projection, secondary gain) rather "
        "than mystical vocabulary. No diagnoses, no therapy clichés."
    ),
    style_mod.LOGIC: (
        " VOICE — analyst: impersonal and unemotional, like a case note. State the "
        "configuration, what follows from it, and where it contradicts itself. No mystical "
        "vocabulary, no comfort, no encouragement, no rhetorical questions, no warmth."
    ),
    style_mod.BUDDY: (
        " VOICE — a close friend who doesn't sugar-coat: informal, blunt, profane. Swear "
        "naturally and freely in the language you are writing in, strong obscenity included. "
        "Say the uncomfortable part out loud, call things what they are, never soften a "
        "reading to spare feelings and never apologise for it. No mystical solemnity."
    ),
}

_FUTURE_BASE = (
    "You are an experienced reader of the Thoth Tarot (Crowley–Harris deck). "
    "This is the one reading where the querent has explicitly asked you to look "
    "AHEAD: given the spread already laid, describe the likely trajectory and "
    "where these forces are heading. Stay grounded in the Thoth meanings of the "
    "cards; be concrete, not vague or grandiose. "
    "Write in {lang}. Answer directly, no preamble. "
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


def _voice(style: str | None) -> str:
    return _STYLE_VOICES.get(style_mod.normalize(style), "")


def system_prompt(
    lang: str, deep: bool = False, memory: bool = False, style: str | None = None
) -> str:
    """Reader persona. Brief by default; ``deep`` is the expanded reading.
    ``memory`` adds the rules for using the querent's past readings; ``style``
    is the querent's chosen voice (``bot/style.py``)."""
    base = _BASE.format(lang=_LANG_INSTRUCTION.get(lang, "English"))
    return base + (_DEEP if deep else _BRIEF) + (_MEMORY_RULE if memory else "") + _voice(style)


def future_system_prompt(
    lang: str, deep: bool = False, memory: bool = False, style: str | None = None
) -> str:
    base = _FUTURE_BASE.format(lang=_LANG_INSTRUCTION.get(lang, "English"))
    return base + (_DEEP if deep else _BRIEF) + (_MEMORY_RULE if memory else "") + _voice(style)


def build_expand_user(context_block: str, short_text: str) -> str:
    """Ask for the expanded version of a reading already given briefly."""
    return (
        f"{context_block}\n\n"
        "The querent was given this SHORT reading:\n"
        f"«{short_text.strip()}»\n\n"
        "They have now asked for the full, expanded reading of the same cards."
    )


def _with_memory(body: str, memory: str | None) -> str:
    """Slot the memory block (``bot.memory.render_block``) in front of the
    closing instruction, or leave the prompt exactly as it was without one."""
    return f"{memory.strip()}\n\n{body}" if memory and memory.strip() else body


def build_daily_user(card_ids: list[str], lang: str, memory: str | None = None) -> str:
    return (
        "Three cards were drawn for the querent's disposition today:\n"
        f"{_cards_block(card_ids, lang)}\n\n"
        + _with_memory(
            "Interpret this three-card spread as the querent's current disposition.", memory
        )
    )


def build_context_user(
    card_ids: list[str], situation: str, lang: str, memory: str | None = None
) -> str:
    return (
        "The querent describes this situation:\n"
        f"«{situation.strip()}»\n\n"
        "Three cards were drawn to read that situation:\n"
        f"{_cards_block(card_ids, lang)}\n\n"
        + _with_memory(
            "Interpret this three-card spread as the current disposition of the "
            "described situation specifically.",
            memory,
        )
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

    async def _complete(self, system: str, user: str, max_tokens: int | None = None) -> str:
        resp = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens or self._max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in resp.content if b.type == "text").strip()

    async def expand(
        self,
        context_block: str,
        short_text: str,
        lang: str,
        *,
        future: bool = False,
        memory: bool = False,
        style: str | None = None,
    ) -> str:
        """The expanded reading of cards already read briefly. ``context_block``
        is the original user prompt (from one of the ``build_*_user`` helpers);
        ``memory`` says whether that block already carries a memory section."""
        maker = future_system_prompt if future else system_prompt
        return await self._complete(
            maker(lang, deep=True, memory=memory, style=style),
            build_expand_user(context_block, short_text),
            max_tokens=2500,
        )

    async def daily(
        self, card_ids: list[str], lang: str, memory: str | None = None, style: str | None = None
    ) -> str:
        return await self._complete(
            system_prompt(lang, memory=bool(memory), style=style),
            build_daily_user(card_ids, lang, memory),
        )

    async def context(
        self,
        card_ids: list[str],
        situation: str,
        lang: str,
        memory: str | None = None,
        style: str | None = None,
    ) -> str:
        return await self._complete(
            system_prompt(lang, memory=bool(memory), style=style),
            build_context_user(card_ids, situation, lang, memory),
        )

    async def future(
        self,
        card_ids: list[str],
        base_interpretation: str,
        lang: str,
        style: str | None = None,
    ) -> str:
        return await self._complete(
            future_system_prompt(lang, style=style),
            build_future_user(card_ids, base_interpretation, lang),
        )

    async def extra(
        self,
        base_card_ids: list[str],
        base_interpretation: str,
        extra_card_ids: list[str],
        lang: str,
        style: str | None = None,
    ) -> str:
        return await self._complete(
            system_prompt(lang, style=style),
            build_extra_user(base_card_ids, base_interpretation, extra_card_ids, lang),
        )
