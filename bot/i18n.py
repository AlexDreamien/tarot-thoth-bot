"""UI translations (ru / uk / en).

Pure core, unit-tested. ``t(lang, key, **kwargs)`` looks up a string and
applies ``str.format``. Every key must exist in all three languages — a
regression test enforces matching key sets, and lookup falls back ru→en→key so
a missing string never crashes a handler.
"""

from __future__ import annotations

LANGS = ("ru", "uk", "en")
DEFAULT_LANG = "ru"

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "lang_name": "English",
        "start": (
            "🔮 <b>Thoth Tarot</b>\n\n"
            "I draw you three cards from the Thoth deck each day and explain your "
            "<b>current disposition</b> — where you stand right now, not what the "
            "future holds.\n\n"
            "Your daily spread is fixed for the day: it won't change until midnight.\n\n"
            "Send /tarot for today's spread, /lang to switch language, /help for more."
        ),
        "help": (
            "🔮 <b>How it works</b>\n\n"
            "• /tarot — your three-card spread for today with a reading of your "
            "current disposition (no fortune-telling). Free, one per day, fixed.\n\n"
            "<b>Paid add-ons</b> (Telegram Stars ⭐), offered after a spread:\n"
            "• Describe a situation — a fresh spread read for that exact situation "
            "(⭐{context}).\n"
            "• Add a look at the future to a spread (⭐{future}).\n"
            "• Two clarifying cards for a spread (⭐{extra2}).\n"
            "• Five clarifying cards for a spread (⭐{extra5}).\n\n"
            "/lang — change language."
        ),
        "lang_prompt": "Choose your language:",
        "lang_set": "Language set to <b>English</b>.",
        "daily_header": "🔮 <b>Your spread for {date}</b>",
        "cards_line": "Cards: {cards}",
        "generating": "🔮 Reading the cards…",
        "error_generic": "Something went wrong reading the cards. Try again in a moment.",
        "offers_title": "Want to go deeper?",
        "btn_future": "🔭 Add the future — ⭐{future}",
        "btn_extra2": "➕ Two clarifying cards — ⭐{extra2}",
        "btn_extra5": "➕ Five clarifying cards — ⭐{extra5}",
        "btn_context": "✍️ Read a specific situation — ⭐{context}",
        "context_prompt": (
            "✍️ Describe the situation in a message, and I'll lay a fresh three-card "
            "spread read specifically for it (⭐{context}). Send /cancel to abort."
        ),
        "context_header": "🔮 <b>Reading for your situation</b>",
        "future_header": "🔭 <b>A look at the future</b>",
        "extra_header": "➕ <b>{n} clarifying cards</b>",
        "no_spread_yet": "Draw a spread first with /tarot.",
        "cancelled": "Cancelled.",
        "invoice_title_context": "Reading for a situation",
        "invoice_desc_context": "A fresh three-card Thoth spread read for the situation you describe.",
        "invoice_title_future": "A look at the future",
        "invoice_desc_future": "Extend your spread with a future-looking reading.",
        "invoice_title_extra2": "Two clarifying cards",
        "invoice_desc_extra2": "Add two cards to your spread and read them within it.",
        "invoice_title_extra5": "Five clarifying cards",
        "invoice_desc_extra5": "Add five cards to your spread and read them within it.",
        "pay_thanks": "Thank you! ⭐ Here you go:",
        "stats": "👤 Users: {users}\n🃏 Spreads: {spreads}\n⭐ Purchases: {purchases} ({stars}⭐)",
    },
    "ru": {
        "lang_name": "Русский",
        "start": (
            "🔮 <b>Таро Тота</b>\n\n"
            "Каждый день я вытягиваю тебе три карты из колоды Тота и объясняю твою "
            "<b>текущую диспозицию</b> — где ты сейчас, а не что будет в будущем.\n\n"
            "Расклад на день фиксирован: он не изменится до полуночи.\n\n"
            "Отправь /tarot для расклада на сегодня, /lang — сменить язык, /help — подробнее."
        ),
        "help": (
            "🔮 <b>Как это работает</b>\n\n"
            "• /tarot — три карты на сегодня с толкованием твоей текущей диспозиции "
            "(без предсказаний). Бесплатно, один раз в день, фиксировано.\n\n"
            "<b>Платные дополнения</b> (Telegram Stars ⭐), предлагаются после расклада:\n"
            "• Опиши ситуацию — отдельный расклад именно под неё (⭐{context}).\n"
            "• Добавить взгляд в будущее к раскладу (⭐{future}).\n"
            "• Две уточняющие карты к раскладу (⭐{extra2}).\n"
            "• Пять уточняющих карт к раскладу (⭐{extra5}).\n\n"
            "/lang — сменить язык."
        ),
        "lang_prompt": "Выбери язык:",
        "lang_set": "Язык установлен: <b>Русский</b>.",
        "daily_header": "🔮 <b>Твой расклад на {date}</b>",
        "cards_line": "Карты: {cards}",
        "generating": "🔮 Читаю карты…",
        "error_generic": "Не удалось прочитать карты. Попробуй ещё раз через минуту.",
        "offers_title": "Хочешь копнуть глубже?",
        "btn_future": "🔭 Добавить будущее — ⭐{future}",
        "btn_extra2": "➕ Две уточняющие карты — ⭐{extra2}",
        "btn_extra5": "➕ Пять уточняющих карт — ⭐{extra5}",
        "btn_context": "✍️ Расклад под ситуацию — ⭐{context}",
        "context_prompt": (
            "✍️ Опиши ситуацию в сообщении — я сделаю отдельный расклад из трёх карт "
            "именно под неё (⭐{context}). /cancel — отменить."
        ),
        "context_header": "🔮 <b>Расклад под твою ситуацию</b>",
        "future_header": "🔭 <b>Взгляд в будущее</b>",
        "extra_header": "➕ <b>{n} уточняющих карт</b>",
        "no_spread_yet": "Сначала сделай расклад командой /tarot.",
        "cancelled": "Отменено.",
        "invoice_title_context": "Расклад под ситуацию",
        "invoice_desc_context": "Отдельный расклад из трёх карт Тота под описанную тобой ситуацию.",
        "invoice_title_future": "Взгляд в будущее",
        "invoice_desc_future": "Дополнить расклад толкованием, направленным в будущее.",
        "invoice_title_extra2": "Две уточняющие карты",
        "invoice_desc_extra2": "Добавить две карты к раскладу и истолковать их в его рамках.",
        "invoice_title_extra5": "Пять уточняющих карт",
        "invoice_desc_extra5": "Добавить пять карт к раскладу и истолковать их в его рамках.",
        "pay_thanks": "Спасибо! ⭐ Держи:",
        "stats": "👤 Пользователей: {users}\n🃏 Раскладов: {spreads}\n⭐ Покупок: {purchases} ({stars}⭐)",
    },
    "uk": {
        "lang_name": "Українська",
        "start": (
            "🔮 <b>Таро Тота</b>\n\n"
            "Щодня я витягую тобі три карти з колоди Тота й пояснюю твою "
            "<b>поточну диспозицію</b> — де ти зараз, а не що буде в майбутньому.\n\n"
            "Розклад на день зафіксований: він не зміниться до опівночі.\n\n"
            "Надішли /tarot для розкладу на сьогодні, /lang — змінити мову, /help — докладніше."
        ),
        "help": (
            "🔮 <b>Як це працює</b>\n\n"
            "• /tarot — три карти на сьогодні з тлумаченням твоєї поточної диспозиції "
            "(без передбачень). Безкоштовно, раз на день, зафіксовано.\n\n"
            "<b>Платні доповнення</b> (Telegram Stars ⭐), пропонуються після розкладу:\n"
            "• Опиши ситуацію — окремий розклад саме під неї (⭐{context}).\n"
            "• Додати погляд у майбутнє до розкладу (⭐{future}).\n"
            "• Дві уточнювальні карти до розкладу (⭐{extra2}).\n"
            "• П'ять уточнювальних карт до розкладу (⭐{extra5}).\n\n"
            "/lang — змінити мову."
        ),
        "lang_prompt": "Обери мову:",
        "lang_set": "Мову встановлено: <b>Українська</b>.",
        "daily_header": "🔮 <b>Твій розклад на {date}</b>",
        "cards_line": "Карти: {cards}",
        "generating": "🔮 Читаю карти…",
        "error_generic": "Не вдалося прочитати карти. Спробуй ще раз за хвилину.",
        "offers_title": "Хочеш копнути глибше?",
        "btn_future": "🔭 Додати майбутнє — ⭐{future}",
        "btn_extra2": "➕ Дві уточнювальні карти — ⭐{extra2}",
        "btn_extra5": "➕ П'ять уточнювальних карт — ⭐{extra5}",
        "btn_context": "✍️ Розклад під ситуацію — ⭐{context}",
        "context_prompt": (
            "✍️ Опиши ситуацію в повідомленні — я зроблю окремий розклад із трьох карт "
            "саме під неї (⭐{context}). /cancel — скасувати."
        ),
        "context_header": "🔮 <b>Розклад під твою ситуацію</b>",
        "future_header": "🔭 <b>Погляд у майбутнє</b>",
        "extra_header": "➕ <b>{n} уточнювальних карт</b>",
        "no_spread_yet": "Спочатку зроби розклад командою /tarot.",
        "cancelled": "Скасовано.",
        "invoice_title_context": "Розклад під ситуацію",
        "invoice_desc_context": "Окремий розклад із трьох карт Тота під описану тобою ситуацію.",
        "invoice_title_future": "Погляд у майбутнє",
        "invoice_desc_future": "Доповнити розклад тлумаченням, спрямованим у майбутнє.",
        "invoice_title_extra2": "Дві уточнювальні карти",
        "invoice_desc_extra2": "Додати дві карти до розкладу й витлумачити їх у його межах.",
        "invoice_title_extra5": "П'ять уточнювальних карт",
        "invoice_desc_extra5": "Додати п'ять карт до розкладу й витлумачити їх у його межах.",
        "pay_thanks": "Дякую! ⭐ Тримай:",
        "stats": "👤 Користувачів: {users}\n🃏 Розкладів: {spreads}\n⭐ Покупок: {purchases} ({stars}⭐)",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    """Translate ``key`` into ``lang``, formatting with ``kwargs``.

    Falls back ru→en→raw-key so a missing translation degrades gracefully.
    """
    table = _STRINGS.get(lang) or _STRINGS[DEFAULT_LANG]
    template = table.get(key)
    if template is None:
        template = _STRINGS[DEFAULT_LANG].get(key) or _STRINGS["en"].get(key) or key
    try:
        return template.format(**kwargs) if kwargs else template
    except (KeyError, IndexError):
        return template
