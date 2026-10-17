"""Bitta e'lonni ko'rish va egasi tomonidan boshqarish.

E'lon o'chirilmaydi: egasi uni «Qaytarildi» deb belgilaydi yoki bekor qiladi.
Inline tugmadagi ma'lumotga ishonib bo'lmaydi (uni soxtalashtirish mumkin),
shuning uchun egalik har safar bazada qayta tekshiriladi.
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from topdim.db import queries
from topdim.db.database import Database
from topdim.db.models import Item, ItemStatus
from topdim.handlers.utils import edit_card
from topdim.keyboards import inline
from topdim.keyboards.inline import ItemAction, ItemCallback
from topdim.locales import uz
from topdim.services.cards import format_item_card

router = Router(name="items")


async def load_item(callback: CallbackQuery, db: Database, item_id: int) -> Item | None:
    """E'lonni yuklaydi. Topilmasa foydalanuvchiga xabar beradi."""
    item = await queries.get_item(db, item_id)
    if item is None:
        await callback.answer(uz.ITEM_NOT_FOUND, show_alert=True)
    return item


@router.callback_query(ItemCallback.filter(F.action == ItemAction.VIEW))
async def view_item(callback: CallbackQuery, callback_data: ItemCallback, db: Database) -> None:
    item = await load_item(callback, db, callback_data.item_id)
    if item is None:
        return
    is_owner = item.owner_id == callback.from_user.id
    # Yopilgan e'lonni faqat egasi ko'ra oladi
    if item.status is not ItemStatus.ACTIVE and not is_owner:
        await callback.answer(uz.ITEM_NOT_FOUND, show_alert=True)
        return

    markup = inline.owner_actions(item) if is_owner else None
    text = format_item_card(item)
    if item.photo_file_id:
        await callback.message.answer_photo(item.photo_file_id, caption=text, reply_markup=markup)
    else:
        await callback.message.answer(text, reply_markup=markup)
    await callback.answer()


# Har bir «so'rash» amali uchun: (tasdiqlovchi amal, «Ha» tugmasi matni, savol)
CONFIRMATIONS = {
    ItemAction.ASK_RETURNED: (ItemAction.DO_RETURNED, uz.BTN_YES_RETURNED, uz.CONFIRM_MARK_RETURNED),
    ItemAction.ASK_CANCEL: (ItemAction.DO_CANCEL, uz.BTN_YES_CANCEL, uz.CONFIRM_CANCEL_ITEM),
}

# Har bir bajariluvchi amal uchun: (yangi holat, muvaffaqiyat xabari)
CLOSINGS = {
    ItemAction.DO_RETURNED: (ItemStatus.RETURNED, uz.STATUS_UPDATED_RETURNED),
    ItemAction.DO_CANCEL: (ItemStatus.CANCELLED, uz.STATUS_UPDATED_CANCELLED),
}


async def load_own_active_item(callback: CallbackQuery, db: Database, item_id: int) -> Item | None:
    """E'lon mavjud, shu foydalanuvchiniki va faol ekanini tekshiradi."""
    item = await load_item(callback, db, item_id)
    if item is None:
        return None
    if item.owner_id != callback.from_user.id:
        await callback.answer(uz.ITEM_NOT_YOURS, show_alert=True)
        return None
    if item.status is not ItemStatus.ACTIVE:
        await callback.answer(uz.ITEM_NOT_ACTIVE, show_alert=True)
        return None
    return item


@router.callback_query(ItemCallback.filter(F.action.in_(CONFIRMATIONS.keys())))
async def ask_confirmation(callback: CallbackQuery, callback_data: ItemCallback, db: Database) -> None:
    """Tugmalarni «Ha / Yo'q» ga almashtiradi."""
    item = await load_own_active_item(callback, db, callback_data.item_id)
    if item is None:
        return
    do_action, yes_text, question = CONFIRMATIONS[callback_data.action]
    await callback.message.edit_reply_markup(
        reply_markup=inline.confirm_action(item.id, do_action, yes_text)
    )
    await callback.answer(question)


@router.callback_query(ItemCallback.filter(F.action == ItemAction.BACK))
async def back_to_actions(callback: CallbackQuery, callback_data: ItemCallback, db: Database) -> None:
    item = await load_item(callback, db, callback_data.item_id)
    if item is None:
        return
    markup = inline.owner_actions(item) if item.owner_id == callback.from_user.id else None
    await callback.message.edit_reply_markup(reply_markup=markup)
    await callback.answer()


@router.callback_query(ItemCallback.filter(F.action.in_(CLOSINGS.keys())))
async def close_item(callback: CallbackQuery, callback_data: ItemCallback, db: Database) -> None:
    """E'lon holatini o'zgartiradi va kartochkani yangilaydi."""
    item = await load_own_active_item(callback, db, callback_data.item_id)
    if item is None:
        return
    new_status, success_text = CLOSINGS[callback_data.action]
    if not await queries.close_item(db, item.id, callback.from_user.id, new_status):
        await callback.answer(uz.ITEM_NOT_ACTIVE, show_alert=True)
        return

    updated = await queries.get_item(db, item.id)
    if isinstance(callback.message, Message):
        await edit_card(callback.message, format_item_card(updated), markup=None)
    await callback.answer(success_text, show_alert=True)
