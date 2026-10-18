"""Barcha routerlar. Tartib muhim: aiogram routerlarni shu tartibda tekshiradi."""

from aiogram import Router

from topdim.handlers import app_login, common, fallback, items, my_items, new_item, search


def get_routers() -> list[Router]:
    return [
        app_login.router,  # /start login_... — oddiy /start'dan oldin
        common.router,    # /start va «Bekor qilish»
        new_item.router,
        search.router,
        my_items.router,
        items.router,
        fallback.router,  # tushunarsiz xabarlar — har doim oxirida
    ]
