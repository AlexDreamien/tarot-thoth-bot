"""UI translations (ru / uk / en).

Pure core, unit-tested. ``t(lang, key, **kwargs)`` looks up a string and
applies ``str.format``. Every key must exist in all three languages — a
regression test enforces matching key sets, and lookup falls back ru→en→key so
a missing string never crashes a handler.
"""

from __future__ import annotations

import random

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
            "Send /tarot for today's spread, /settings to set it up, /help for more."
        ),
        "help": (
            "🔮 <b>How it works</b>\n\n"
            "• /tarot — your three-card spread for today with a reading of your "
            "current disposition (no fortune-telling). One per day, fixed.\n\n"
            "After a spread you can add, right from the buttons: a look at the "
            "future, extra clarifying cards, or a reading for a specific "
            "situation you describe.\n\n"
            "/history — browse and revisit your past readings.\n"
            "/settings — reminder, voice of the readings, language."
        ),
        "lang_prompt": "Choose your language:",
        "lang_set": "Language set to <b>English</b>.",
        "daily_header": "🔮 <b>Your spread for {date}</b>",
        "cards_line": "Cards: {cards}",
        "generating": "🔮 Composing your reading…",
        "error_generic": "Something went wrong reading the cards. Try again in a moment.",
        "btn_future": "🔭 A look at the future",
        "btn_extra2": "🃏 Two clarifying cards",
        "btn_extra5": "🃏 Five clarifying cards",
        "btn_extra3": "🃏 Three more cards (up to five)",
        "btn_context": "✍️ Read a specific situation",
        "btn_expand": "🔍 Expand this reading",
        "btn_newday": "🌅 Reading for a new day",
        "price_suffix": " — ⭐{stars}",
        "expand_header": "🔍 <b>In full</b>",
        "already_expanded": "This reading is already expanded.",
        "newday_already": (
            "🌅 You already have today's reading. A new one comes tomorrow — "
            "but you can lay a spread for a specific situation right now."
        ),
        "invoice_title_expand": "Expanded reading",
        "invoice_desc_expand": "The full, detailed version of this reading.",
        "settings_title": "⚙️ <b>Settings</b>\n\nDaily reminder: {state}",
        "settings_state_on": "every day at {hour}:00 (UTC{offset})",
        "settings_state_off": "off — I'll nudge you once a week instead",
        "btn_set_time": "🕘 Reminder time",
        "btn_set_tz": "🌍 Time zone (now UTC{offset})",
        "btn_set_lang": "🌐 Language: {name}",
        "btn_set_address": "🙋 How to address you: {summary}",
        "btn_set_bio": "📝 About you: {summary}",
        "btn_premium": "💎 Premium: {state}",
        "premium_on": "until {date}",
        "premium_off": "not active",
        "premium_title_on": (
            "💎 <b>Premium</b>\n\nActive until <b>{date}</b>.\n\n"
            "Paid packages with extra features are on the way."
        ),
        "premium_title_off": (
            "💎 <b>Premium</b>\n\nNot active right now.\n\n"
            "Paid packages with extra features are on the way."
        ),
        "bio_set": "filled in",
        "bio_unset": "empty",
        "bio_title": (
            "📝 <b>About you</b>\n\n{bio}\n\n"
            "A few lines about yourself — what you do, what you're going through, "
            "what matters right now. I'll keep it in mind in every reading. Optional."
        ),
        "bio_empty": "<i>Nothing yet.</i>",
        "btn_edit_bio": "✏️ Write about yourself",
        "btn_clear_bio": "🧹 Clear",
        "bio_prompt": "Send a few lines about yourself. /cancel to abort.",
        "bio_saved": "✅ Noted. I'll keep it in mind.",
        "bio_cleared": "✅ Cleared.",
        "bio_too_long": "A bit long — please keep it under {limit} characters (yours is {got}).",
        "onboarding": (
            "👋 Before your first spread — set me up a little.\n\n"
            "Tell me <b>about yourself</b> and I'll read with that in mind; pick the "
            "<b>voice</b> you want the readings in, and your <b>language</b>.\n\n"
            "All optional — /tarot works right now either way."
        ),
        "btn_open_settings": "⚙️ Open settings",
        "address_title": (
            "🙋 <b>How should I address you?</b>\n\n"
            "Gender: {gender}\nName: {name}\n\n"
            "With no gender set I'll write to you without gendered wording."
        ),
        "address_unset": "not set",
        "gender_m": "male",
        "gender_f": "female",
        "btn_gender_m": "♂ Male",
        "btn_gender_f": "♀ Female",
        "btn_gender_none": "🚫 Don't specify",
        "btn_set_name": "✏️ Set a name",
        "btn_clear_name": "🧹 Forget my name",
        "name_prompt": "Send the name you'd like me to use. /cancel to abort.",
        "name_saved": "✅ I'll call you {name}.",
        "name_cleared": "✅ I won't use a name.",
        "name_too_odd": "That doesn't look like a name — send a short one, please.",
        "btn_set_style": "🎭 Voice: {style}",
        "pick_style": "Pick the voice of your readings:",
        "style_saved": "✅ Voice: {style}",
        "style_fortune": "🔮 Fortune-teller",
        "style_psy": "🧠 Psychologist",
        "style_logic": "📐 Logician",
        "style_buddy": "🍻 Mate",
        "btn_reminder_off": "🔕 Turn reminders off",
        "btn_reminder_on": "🔔 Turn reminders on",
        "pick_hour": "Pick the hour (your local time):",
        "pick_tz": "Pick your UTC offset:",
        "settings_saved": "✅ Saved: {state}",
        "reminder_msg": "🌅 Good morning! Your Thoth reading for today is ready to be drawn.",
        "weekly_msg": "🔮 It's been a while — want a reading? Reminders are off; /settings to change.",
        "context_prompt": (
            "✍️ Describe the situation in a message, and I'll lay a fresh three-card "
            "spread read specifically for it. Send /cancel to abort."
        ),
        "context_header": "🔮 <b>Reading for your situation</b>",
        "future_header": "🔭 <b>A look at the future</b>",
        "extra_header": "➕ <b>{n} clarifying cards</b>",
        "no_spread_yet": "Draw a spread first with /tarot.",
        "already_bought": "You've already added this to this spread.",
        "cancelled": "Cancelled.",
        "hist_title": "🗓 <b>Your past readings.</b> Pick a date:",
        "hist_empty": "You have no readings yet. Draw your first with /tarot.",
        "hist_pick": "Several readings that day — pick one:",
        "hist_daily_label": "🔮 Daily reading",
        "hist_back": "◀ Back to calendar",
        "hist_replay_daily": "🗓 <b>Reading · {date}</b>",
        "hist_replay_context": "🗓 <b>Reading for a situation · {date}</b>",
        "hist_situation": "✍️ Request: {situation}",
        "invoice_title_context": "Reading for a situation",
        "invoice_desc_context": "A fresh three-card Thoth spread read for the situation you describe.",
        "invoice_title_future": "A look at the future",
        "invoice_desc_future": "Extend your spread with a future-looking reading.",
        "invoice_title_extra2": "Two clarifying cards",
        "invoice_desc_extra2": "Add two cards to your spread and read them within it.",
        "invoice_title_extra5": "Five clarifying cards",
        "invoice_desc_extra5": "Add five cards to your spread and read them within it.",
        "invoice_title_extra3": "Three more clarifying cards",
        "invoice_desc_extra3": "Add three more cards to your spread — five clarifying cards in total.",
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
            "Отправь /tarot для расклада на сегодня, /settings — настроить, /help — подробнее."
        ),
        "help": (
            "🔮 <b>Как это работает</b>\n\n"
            "• /tarot — три карты на сегодня с толкованием твоей текущей диспозиции "
            "(без предсказаний). Один раз в день, фиксировано.\n\n"
            "После расклада прямо на кнопках можно добавить: взгляд в будущее, "
            "уточняющие карты или расклад под конкретную ситуацию.\n\n"
            "/history — смотреть и повторять свои прошлые расклады.\n"
            "/settings — напоминание, стиль толкований, язык."
        ),
        "lang_prompt": "Выбери язык:",
        "lang_set": "Язык установлен: <b>Русский</b>.",
        "daily_header": "🔮 <b>Твой расклад на {date}</b>",
        "cards_line": "Карты: {cards}",
        "generating": "🔮 Составляю предсказание…",
        "error_generic": "Не удалось прочитать карты. Попробуй ещё раз через минуту.",
        "btn_future": "🔭 Взгляд в будущее",
        "btn_extra2": "🃏 Две уточняющие карты",
        "btn_extra5": "🃏 Пять уточняющих карт",
        "btn_extra3": "🃏 Ещё 3 карты (до пяти)",
        "btn_context": "✍️ Расклад под ситуацию",
        "btn_expand": "🔍 Раскрыть подробнее",
        "btn_newday": "🌅 Расклад на новый день",
        "price_suffix": " — ⭐{stars}",
        "expand_header": "🔍 <b>Подробно</b>",
        "already_expanded": "Это толкование уже раскрыто.",
        "newday_already": (
            "🌅 Расклад на сегодня у тебя уже есть — новый будет завтра. "
            "Но прямо сейчас можно сделать расклад под конкретную ситуацию."
        ),
        "invoice_title_expand": "Развёрнутое толкование",
        "invoice_desc_expand": "Полная, подробная версия этого толкования.",
        "settings_title": "⚙️ <b>Настройки</b>\n\nЕжедневное напоминание: {state}",
        "settings_state_on": "каждый день в {hour}:00 (UTC{offset})",
        "settings_state_off": "выключено — напомню раз в неделю",
        "btn_set_time": "🕘 Время напоминания",
        "btn_set_tz": "🌍 Часовой пояс (сейчас UTC{offset})",
        "btn_set_lang": "🌐 Язык: {name}",
        "btn_set_address": "🙋 Обращение: {summary}",
        "btn_set_bio": "📝 О себе: {summary}",
        "btn_premium": "💎 Premium: {state}",
        "premium_on": "до {date}",
        "premium_off": "не активен",
        "premium_title_on": (
            "💎 <b>Premium</b>\n\nАктивен до <b>{date}</b>.\n\n"
            "Платные пакеты с дополнительными возможностями появятся позже."
        ),
        "premium_title_off": (
            "💎 <b>Premium</b>\n\nСейчас не активен.\n\n"
            "Платные пакеты с дополнительными возможностями появятся позже."
        ),
        "bio_set": "заполнено",
        "bio_unset": "пусто",
        "bio_title": (
            "📝 <b>О себе</b>\n\n{bio}\n\n"
            "Несколько строк о себе — чем занимаешься, что сейчас происходит, "
            "что для тебя важно. Буду держать это в уме в каждом раскладе. По желанию."
        ),
        "bio_empty": "<i>Пока пусто.</i>",
        "btn_edit_bio": "✏️ Рассказать о себе",
        "btn_clear_bio": "🧹 Очистить",
        "bio_prompt": "Пришли несколько строк о себе. /cancel — отмена.",
        "bio_saved": "✅ Запомнил. Буду учитывать.",
        "bio_cleared": "✅ Очищено.",
        "bio_too_long": "Многовато — уложись в {limit} знаков (у тебя {got}).",
        "onboarding": (
            "👋 Перед первым раскладом — давай немного настроимся.\n\n"
            "Расскажи <b>о себе</b>, и я буду это учитывать; выбери <b>стиль</b>, "
            "в котором хочешь получать толкования, и <b>язык</b>.\n\n"
            "Всё по желанию — /tarot работает и так, прямо сейчас."
        ),
        "btn_open_settings": "⚙️ Открыть настройки",
        "address_title": (
            "🙋 <b>Как к тебе обращаться?</b>\n\n"
            "Пол: {gender}\nИмя: {name}\n\n"
            "Если пол не указан, буду писать без родовых окончаний."
        ),
        "address_unset": "не указано",
        "gender_m": "мужской",
        "gender_f": "женский",
        "btn_gender_m": "♂ Мужской",
        "btn_gender_f": "♀ Женский",
        "btn_gender_none": "🚫 Не указывать",
        "btn_set_name": "✏️ Задать имя",
        "btn_clear_name": "🧹 Забыть имя",
        "name_prompt": "Пришли имя, которым тебя называть. /cancel — отмена.",
        "name_saved": "✅ Буду обращаться: {name}.",
        "name_cleared": "✅ Имя больше не использую.",
        "name_too_odd": "Это не похоже на имя — пришли что-нибудь покороче.",
        "btn_set_style": "🎭 Стиль: {style}",
        "pick_style": "Выбери стиль толкований:",
        "style_saved": "✅ Стиль: {style}",
        "style_fortune": "🔮 Гадалка",
        "style_psy": "🧠 Психолог",
        "style_logic": "📐 Логик",
        "style_buddy": "🍻 Друган",
        "btn_reminder_off": "🔕 Выключить напоминания",
        "btn_reminder_on": "🔔 Включить напоминания",
        "pick_hour": "Выбери час (по твоему местному времени):",
        "pick_tz": "Выбери свой сдвиг от UTC:",
        "settings_saved": "✅ Сохранено: {state}",
        "reminder_msg": "🌅 Доброе утро! Расклад Таро Тота на сегодня ждёт тебя.",
        "weekly_msg": "🔮 Давно не виделись — сделаем расклад? Напоминания выключены, /settings — изменить.",
        "context_prompt": (
            "✍️ Опиши ситуацию в сообщении — я сделаю отдельный расклад из трёх карт "
            "именно под неё. /cancel — отменить."
        ),
        "context_header": "🔮 <b>Расклад под твою ситуацию</b>",
        "future_header": "🔭 <b>Взгляд в будущее</b>",
        "extra_header": "➕ <b>{n} уточняющих карт</b>",
        "no_spread_yet": "Сначала сделай расклад командой /tarot.",
        "already_bought": "Эта услуга уже добавлена к этому раскладу.",
        "cancelled": "Отменено.",
        "hist_title": "🗓 <b>Твои прошлые расклады.</b> Выбери дату:",
        "hist_empty": "У тебя пока нет раскладов. Сделай первый: /tarot.",
        "hist_pick": "В этот день было несколько раскладов — выбери:",
        "hist_daily_label": "🔮 Ежедневный расклад",
        "hist_back": "◀ К календарю",
        "hist_replay_daily": "🗓 <b>Расклад · {date}</b>",
        "hist_replay_context": "🗓 <b>Расклад под ситуацию · {date}</b>",
        "hist_situation": "✍️ Запрос: {situation}",
        "invoice_title_context": "Расклад под ситуацию",
        "invoice_desc_context": "Отдельный расклад из трёх карт Тота под описанную тобой ситуацию.",
        "invoice_title_future": "Взгляд в будущее",
        "invoice_desc_future": "Дополнить расклад толкованием, направленным в будущее.",
        "invoice_title_extra2": "Две уточняющие карты",
        "invoice_desc_extra2": "Добавить две карты к раскладу и истолковать их в его рамках.",
        "invoice_title_extra5": "Пять уточняющих карт",
        "invoice_desc_extra5": "Добавить пять карт к раскладу и истолковать их в его рамках.",
        "invoice_title_extra3": "Ещё три уточняющие карты",
        "invoice_desc_extra3": "Добавить ещё три карты к раскладу — всего пять уточняющих.",
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
            "Надішли /tarot для розкладу на сьогодні, /settings — налаштувати, /help — докладніше."
        ),
        "help": (
            "🔮 <b>Як це працює</b>\n\n"
            "• /tarot — три карти на сьогодні з тлумаченням твоєї поточної диспозиції "
            "(без передбачень). Раз на день, зафіксовано.\n\n"
            "Після розкладу прямо з кнопок можна додати: погляд у майбутнє, "
            "уточнювальні карти або розклад під конкретну ситуацію.\n\n"
            "/history — переглядати й повторювати свої минулі розклади.\n"
            "/settings — нагадування, стиль тлумачень, мова."
        ),
        "lang_prompt": "Обери мову:",
        "lang_set": "Мову встановлено: <b>Українська</b>.",
        "daily_header": "🔮 <b>Твій розклад на {date}</b>",
        "cards_line": "Карти: {cards}",
        "generating": "🔮 Складаю передбачення…",
        "error_generic": "Не вдалося прочитати карти. Спробуй ще раз за хвилину.",
        "btn_future": "🔭 Погляд у майбутнє",
        "btn_extra2": "🃏 Дві уточнювальні карти",
        "btn_extra5": "🃏 П'ять уточнювальних карт",
        "btn_extra3": "🃏 Ще 3 карти (до п'яти)",
        "btn_context": "✍️ Розклад під ситуацію",
        "btn_expand": "🔍 Розкрити докладніше",
        "btn_newday": "🌅 Розклад на новий день",
        "price_suffix": " — ⭐{stars}",
        "expand_header": "🔍 <b>Докладно</b>",
        "already_expanded": "Це тлумачення вже розкрито.",
        "newday_already": (
            "🌅 Розклад на сьогодні в тебе вже є — новий буде завтра. "
            "Але просто зараз можна зробити розклад під конкретну ситуацію."
        ),
        "invoice_title_expand": "Розгорнуте тлумачення",
        "invoice_desc_expand": "Повна, докладна версія цього тлумачення.",
        "settings_title": "⚙️ <b>Налаштування</b>\n\nЩоденне нагадування: {state}",
        "settings_state_on": "щодня о {hour}:00 (UTC{offset})",
        "settings_state_off": "вимкнено — нагадаю раз на тиждень",
        "btn_set_time": "🕘 Час нагадування",
        "btn_set_tz": "🌍 Часовий пояс (зараз UTC{offset})",
        "btn_set_lang": "🌐 Мова: {name}",
        "btn_set_address": "🙋 Звертання: {summary}",
        "btn_set_bio": "📝 Про себе: {summary}",
        "btn_premium": "💎 Premium: {state}",
        "premium_on": "до {date}",
        "premium_off": "не активний",
        "premium_title_on": (
            "💎 <b>Premium</b>\n\nАктивний до <b>{date}</b>.\n\n"
            "Платні пакети з додатковими можливостями з'являться пізніше."
        ),
        "premium_title_off": (
            "💎 <b>Premium</b>\n\nЗараз не активний.\n\n"
            "Платні пакети з додатковими можливостями з'являться пізніше."
        ),
        "bio_set": "заповнено",
        "bio_unset": "порожньо",
        "bio_title": (
            "📝 <b>Про себе</b>\n\n{bio}\n\n"
            "Кілька рядків про себе — чим займаєшся, що зараз відбувається, "
            "що для тебе важливо. Триматиму це на увазі в кожному розкладі. За бажанням."
        ),
        "bio_empty": "<i>Поки порожньо.</i>",
        "btn_edit_bio": "✏️ Розповісти про себе",
        "btn_clear_bio": "🧹 Очистити",
        "bio_prompt": "Надішли кілька рядків про себе. /cancel — скасувати.",
        "bio_saved": "✅ Запам'ятав. Враховуватиму.",
        "bio_cleared": "✅ Очищено.",
        "bio_too_long": "Забагато — вклади в {limit} знаків (у тебе {got}).",
        "onboarding": (
            "👋 Перед першим розкладом — трохи налаштуймося.\n\n"
            "Розкажи <b>про себе</b>, і я це враховуватиму; обери <b>стиль</b>, "
            "у якому хочеш отримувати тлумачення, і <b>мову</b>.\n\n"
            "Усе за бажанням — /tarot працює й так, просто зараз."
        ),
        "btn_open_settings": "⚙️ Відкрити налаштування",
        "address_title": (
            "🙋 <b>Як до тебе звертатися?</b>\n\n"
            "Стать: {gender}\nІм'я: {name}\n\n"
            "Якщо стать не вказана, писатиму без родових закінчень."
        ),
        "address_unset": "не вказано",
        "gender_m": "чоловіча",
        "gender_f": "жіноча",
        "btn_gender_m": "♂ Чоловіча",
        "btn_gender_f": "♀ Жіноча",
        "btn_gender_none": "🚫 Не вказувати",
        "btn_set_name": "✏️ Задати ім'я",
        "btn_clear_name": "🧹 Забути ім'я",
        "name_prompt": "Надішли ім'я, яким тебе називати. /cancel — скасувати.",
        "name_saved": "✅ Звертатимусь: {name}.",
        "name_cleared": "✅ Ім'я більше не використовую.",
        "name_too_odd": "Це не схоже на ім'я — надішли щось коротше.",
        "btn_set_style": "🎭 Стиль: {style}",
        "pick_style": "Обери стиль тлумачень:",
        "style_saved": "✅ Стиль: {style}",
        "style_fortune": "🔮 Ворожка",
        "style_psy": "🧠 Психолог",
        "style_logic": "📐 Логік",
        "style_buddy": "🍻 Кореш",
        "btn_reminder_off": "🔕 Вимкнути нагадування",
        "btn_reminder_on": "🔔 Увімкнути нагадування",
        "pick_hour": "Обери годину (за твоїм місцевим часом):",
        "pick_tz": "Обери свій зсув від UTC:",
        "settings_saved": "✅ Збережено: {state}",
        "reminder_msg": "🌅 Доброго ранку! Розклад Таро Тота на сьогодні чекає на тебе.",
        "weekly_msg": "🔮 Давно не бачились — зробимо розклад? Нагадування вимкнені, /settings — змінити.",
        "context_prompt": (
            "✍️ Опиши ситуацію в повідомленні — я зроблю окремий розклад із трьох карт "
            "саме під неї. /cancel — скасувати."
        ),
        "context_header": "🔮 <b>Розклад під твою ситуацію</b>",
        "future_header": "🔭 <b>Погляд у майбутнє</b>",
        "extra_header": "➕ <b>{n} уточнювальних карт</b>",
        "no_spread_yet": "Спочатку зроби розклад командою /tarot.",
        "already_bought": "Ця послуга вже додана до цього розкладу.",
        "cancelled": "Скасовано.",
        "hist_title": "🗓 <b>Твої минулі розклади.</b> Обери дату:",
        "hist_empty": "У тебе поки немає розкладів. Зроби перший: /tarot.",
        "hist_pick": "Того дня було кілька розкладів — обери:",
        "hist_daily_label": "🔮 Щоденний розклад",
        "hist_back": "◀ До календаря",
        "hist_replay_daily": "🗓 <b>Розклад · {date}</b>",
        "hist_replay_context": "🗓 <b>Розклад під ситуацію · {date}</b>",
        "hist_situation": "✍️ Запит: {situation}",
        "invoice_title_context": "Розклад під ситуацію",
        "invoice_desc_context": "Окремий розклад із трьох карт Тота під описану тобою ситуацію.",
        "invoice_title_future": "Погляд у майбутнє",
        "invoice_desc_future": "Доповнити розклад тлумаченням, спрямованим у майбутнє.",
        "invoice_title_extra2": "Дві уточнювальні карти",
        "invoice_desc_extra2": "Додати дві карти до розкладу й витлумачити їх у його межах.",
        "invoice_title_extra5": "П'ять уточнювальних карт",
        "invoice_desc_extra5": "Додати п'ять карт до розкладу й витлумачити їх у його межах.",
        "invoice_title_extra3": "Ще три уточнювальні карти",
        "invoice_desc_extra3": "Додати ще три карти до розкладу — усього п'ять уточнювальних.",
        "pay_thanks": "Дякую! ⭐ Тримай:",
        "stats": "👤 Користувачів: {users}\n🃏 Розкладів: {spreads}\n⭐ Покупок: {purchases} ({stars}⭐)",
    },
}


# Calendar labels for the /history view — kept out of _STRINGS (they're lists,
# not template strings, and the key-matching test only covers _STRINGS).
MONTHS = {
    "en": [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ],
    "ru": [
        "Январь",
        "Февраль",
        "Март",
        "Апрель",
        "Май",
        "Июнь",
        "Июль",
        "Август",
        "Сентябрь",
        "Октябрь",
        "Ноябрь",
        "Декабрь",
    ],
    "uk": [
        "Січень",
        "Лютий",
        "Березень",
        "Квітень",
        "Травень",
        "Червень",
        "Липень",
        "Серпень",
        "Вересень",
        "Жовтень",
        "Листопад",
        "Грудень",
    ],
}
WEEKDAYS = {
    "en": ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"],
    "ru": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
    "uk": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"],
}


# The line above the action buttons. A tuple per language rather than a
# _STRINGS entry (like MONTHS/WEEKDAYS), because one is picked at random: these
# buttons follow *every* reading, and hearing the same sentence a dozen times a
# week makes the reader sound like a vending machine. Keep them generic — the
# same line has to sit under a daily spread, a look at the future, clarifying
# cards and an expanded reading alike.
OFFERS_TITLES: dict[str, tuple[str, ...]] = {
    "en": (
        "Want to go deeper?",
        "Shall we go on?",
        "What next?",
        "The cards have more to say.",
        "Worth a closer look.",
        "If you have a question, now's the time.",
        "The table isn't cleared yet.",
        "Where shall we look next?",
    ),
    "ru": (
        "Хочешь копнуть глубже?",
        "Продолжим?",
        "Что дальше?",
        "Карты готовы сказать больше.",
        "Можно посмотреть внимательнее.",
        "Если есть вопрос — самое время.",
        "Стол ещё не убран.",
        "Куда посмотрим дальше?",
    ),
    "uk": (
        "Хочеш копнути глибше?",
        "Продовжимо?",
        "Що далі?",
        "Карти готові сказати більше.",
        "Можна подивитися уважніше.",
        "Якщо є питання — саме час.",
        "Стіл ще не прибрано.",
        "Куди подивимось далі?",
    ),
}


def offers_title(lang: str, n: int | None = None) -> str:
    """One invitation to the action buttons, varied between readings.

    Random by default; pass ``n`` to choose deterministically (it wraps, so any
    integer is valid) — that is what the tests use.
    """
    variants = OFFERS_TITLES.get(lang) or OFFERS_TITLES[DEFAULT_LANG]
    n = random.randrange(len(variants)) if n is None else n
    return variants[n % len(variants)]


def _cal_labels(lang: str):
    lang = lang if lang in MONTHS else DEFAULT_LANG
    return MONTHS[lang], WEEKDAYS[lang]


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
