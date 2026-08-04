import asyncio

import pytest

from bot.handlers.render import TG_LIMIT, answer_long, split_text


class _FakeMessage:
    def __init__(self):
        self.sent: list[str] = []

    async def answer(self, text, **kw):
        self.sent.append(text)


def test_thinking_placeholder_is_shown_then_deleted():
    from bot.handlers.render import thinking

    events: list[str] = []

    class Note:
        async def delete(self):
            events.append("deleted")

    class M:
        async def answer(self, text, **kw):
            events.append(f"sent:{text}")
            return Note()

    async def run():
        async with thinking(M(), "ru"):
            events.append("generating")
        events.append("result")

    asyncio.run(run())
    # placeholder appears first and is gone *before* the reading is sent
    assert events[0].startswith("sent:")
    assert events[1:] == ["generating", "deleted", "result"]


def test_thinking_removes_placeholder_even_when_generation_fails():
    from bot.handlers.render import thinking

    deleted = []

    class Note:
        async def delete(self):
            deleted.append(True)

    class M:
        async def answer(self, text, **kw):
            return Note()

    async def run():
        async with thinking(M(), "ru"):
            raise RuntimeError("model error")

    with pytest.raises(RuntimeError):
        asyncio.run(run())
    assert deleted == [True]


def test_generated_text_is_html_escaped_but_header_is_not():
    # parse_mode is HTML: a stray '<' or '&' from the model would be rejected,
    # while the header's own tags must survive.
    m = _FakeMessage()
    asyncio.run(answer_long(m, "рост <5% и Крылья & Меч", header="<b>Подробно</b>"))
    assert m.sent[0].startswith("<b>Подробно</b>")
    assert "&lt;5%" in m.sent[0]
    assert "&amp;" in m.sent[0]


def test_long_text_is_sent_as_several_messages():
    m = _FakeMessage()
    asyncio.run(answer_long(m, "\n\n".join("абзац " * 200 for _ in range(10))))
    assert len(m.sent) > 1
    assert all(len(s) <= TG_LIMIT for s in m.sent)


def test_short_text_stays_one_chunk():
    assert split_text("hello") == ["hello"]
    assert split_text("") == []


def test_every_chunk_is_within_the_limit():
    # An expanded reading easily exceeds Telegram's 4096-char cap, which used
    # to raise TelegramBadRequest("message is too long").
    text = "\n\n".join(f"Параграф номер {i}. " + "слово " * 80 for i in range(20))
    chunks = split_text(text)
    assert len(chunks) > 1
    assert all(len(c) <= TG_LIMIT for c in chunks)


def test_splits_on_paragraph_boundaries_when_possible():
    para = "x" * 2000
    chunks = split_text(f"{para}\n\n{para}\n\n{para}")
    assert all(len(c) <= TG_LIMIT for c in chunks)
    # nothing is lost
    assert sum(c.count("x") for c in chunks) == 6000


def test_single_huge_paragraph_is_hard_split():
    chunks = split_text("y" * (TG_LIMIT * 2 + 100))
    assert len(chunks) == 3
    assert all(len(c) <= TG_LIMIT for c in chunks)
    assert sum(len(c) for c in chunks) == TG_LIMIT * 2 + 100


def test_content_is_preserved_in_order():
    text = "Первый абзац.\n\n" + ("Второй. " * 700) + "\n\nТретий абзац."
    chunks = split_text(text)
    joined = " ".join(chunks)
    assert joined.startswith("Первый абзац.")
    assert "Третий абзац." in chunks[-1]
