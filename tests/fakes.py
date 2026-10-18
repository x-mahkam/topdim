"""Testlar uchun soxta Telegram sessiyasi.

Haqiqiy Telegram o'rniga ishlaydi: bot yuborgan har bir so'rov
(sendMessage, editMessageText, ...) ``requests`` ro'yxatiga yoziladi, javob
esa soxta bo'ladi. Shunday qilib botni token va internetsiz sinaymiz.
"""

from datetime import datetime
from itertools import count

from aiogram.client.session.base import BaseSession
from aiogram.methods import GetFile, SendMessage, SendPhoto, TelegramMethod
from aiogram.types import Chat, File, Message, PhotoSize

# bot.download() chaqirilganda qaytariladigan "rasm"
FAKE_PHOTO_BYTES = b"\xff\xd8\xff fake jpeg"


class FakeSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.requests: list[TelegramMethod] = []
        self._message_ids = count(1000)

    async def make_request(self, bot, method, timeout=None):
        self.requests.append(method)
        if isinstance(method, (SendMessage, SendPhoto)):
            photo = [PhotoSize(file_id="f", file_unique_id="u", width=1, height=1)] if isinstance(method, SendPhoto) else None
            return Message(
                message_id=next(self._message_ids),
                date=datetime.now(),
                chat=Chat(id=method.chat_id, type="private"),
                text=getattr(method, "text", None),
                caption=getattr(method, "caption", None),
                photo=photo,
            )
        if isinstance(method, GetFile):
            return File(file_id=method.file_id, file_unique_id="u", file_path="photos/file.jpg")
        return True

    async def close(self) -> None:
        pass

    async def stream_content(self, *args, **kwargs):
        yield FAKE_PHOTO_BYTES
