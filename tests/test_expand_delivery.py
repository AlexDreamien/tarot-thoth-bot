"""Every delivery path must end in buttons.

"Expand this reading" was the one that didn't: it sent the long text and left
the chat with no way forward — no add-ons, no new-day, no situation reading.
These drive the handler with fakes (no aiogram, no network, no DB).
"""

import asyncio

import pytest

from bot.handlers import payments


class _Note:
    async def delete(self):
        pass


class FakeMessage:
    """Records what was sent and with which keyboard."""

    def __init__(self):
        self.sent: list[tuple[str, object]] = []

    async def answer(self, text, **kw):
        self.sent.append((text, kw.get("reply_markup")))
        return _Note()

    @property
    def keyboards(self):
        return [m for _, m in self.sent if m is not None]


class FakeCfg:
    payments_enabled = False


class FakeDb:
    def get_extra(self, extra_id):
        return {"spread_id": 42}


def _datas(kb):
    return [b.callback_data for row in kb.inline_keyboard for b in row]


def _run(monkeypatch, kind, target_id, *, available=()):
    async def fake_expanded(*a, **kw):
        return "Развёрнутое толкование."

    async def fake_available(db, spread_id):
        return list(available)

    for name in (
        "ensure_spread_expanded",
        "ensure_future_expanded",
        "ensure_extra_expanded",
    ):
        monkeypatch.setattr(payments, name, fake_expanded)
    monkeypatch.setattr(payments, "available_for_spread", fake_available)

    msg = FakeMessage()
    asyncio.run(payments._deliver_expand(msg, FakeDb(), None, FakeCfg(), "ru", kind, target_id))
    return msg


@pytest.mark.parametrize("kind", ["s", "f", "e"])
def test_expanding_a_reading_leaves_the_chat_with_buttons(monkeypatch, kind):
    msg = _run(monkeypatch, kind, 42)
    assert msg.keyboards, f"expand of kind {kind!r} dead-ends with no keyboard"
    assert _datas(msg.keyboards[-1]) == ["ctx", "newday"]


def test_the_keyboard_targets_the_parent_spread_not_the_clarifying_draw(monkeypatch):
    # For "e" the callback carries an extra_draws id; the buy buttons must point
    # at the spread that owns it (FakeDb maps extra 7 -> spread 42).
    from bot import pricing

    msg = _run(monkeypatch, "e", 7, available=[pricing.FUTURE])
    assert f"buy:{pricing.FUTURE}:42" in _datas(msg.keyboards[-1])


def test_the_expanded_reading_is_not_offered_for_expansion_again(monkeypatch):
    # Its long text is cached — tapping again would just repeat the screen.
    msg = _run(monkeypatch, "s", 42)
    assert not any(d.startswith("exp:") for d in _datas(msg.keyboards[-1]))


def test_the_long_text_is_still_sent_before_the_buttons(monkeypatch):
    msg = _run(monkeypatch, "s", 42)
    texts = [t for t, _ in msg.sent]
    assert any("Развёрнутое толкование." in t for t in texts)
    assert msg.sent[-1][1] is not None  # buttons come last
