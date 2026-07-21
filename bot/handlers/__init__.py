"""aiogram routers (thin layer). ``all_routers()`` returns them in include order."""

from __future__ import annotations

from aiogram import Router


def all_routers() -> list[Router]:
    from . import common, payments, spread

    return [common.router, spread.router, payments.router]
