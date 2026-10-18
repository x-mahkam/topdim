"""Botning barcha matnlari (o'zbek tili, lotin yozuvi).

Matnlarni bitta faylda saqlash afzalliklari:
  * matnni o'zgartirish uchun kodni titkilash shart emas;
  * keyinchalik boshqa til qo'shish oson (masalan, locales/ru.py);
  * tugma matnlari handlerlarda ham shu yerdan olinadi, shuning uchun
    tugma matni o'zgarsa, uni "tutib oladigan" kod ham avtomatik moslashadi.

Matnlarda HTML teglari (<b>, <i>) ishlatiladi — bot HTML rejimida ishlaydi.
"""

# ---------------------------------------------------------------------------
# Asosiy menyu tugmalari
# ---------------------------------------------------------------------------
BTN_LOST = "😟 Buyumim yo'qoldi"
BTN_FOUND = "🎁 Buyum topdim"
BTN_SEARCH = "🔎 Qidirish"
BTN_MY_ITEMS = "📋 Mening e'lonlarim"
BTN_HELP = "ℹ️ Yordam"

# Umumiy tugmalar
BTN_CANCEL = "❌ Bekor qilish"
BTN_SKIP = "⏭ O'tkazib yuborish"
BTN_CONFIRM = "✅ Tasdiqlash"

# Sana tugmalari
BTN_TODAY = "Bugun"
BTN_YESTERDAY = "Kecha"
BTN_ENTER_DATE = "📅 Sanani kiritish"

# Qidiruvdagi "hammasi" tugmasi
BTN_ALL_CATEGORIES = "🗂 Barcha kategoriyalar"

# ---------------------------------------------------------------------------
# Kategoriyalar va joylar.
# Bazada qisqa inglizcha kod saqlanadi (masalan, "keys"), foydalanuvchiga esa
# chiroyli o'zbekcha nom ko'rsatiladi. Shunda nomni o'zgartirsak ham eski
# e'lonlar buzilmaydi.
# ---------------------------------------------------------------------------
CATEGORIES: dict[str, str] = {
    "document": "📄 Hujjat",
    "electronics": "📱 Telefon/elektronika",
    "keys": "🔑 Kalit",
    "bag": "👜 Sumka/hamyon",
    "clothes": "👕 Kiyim",
    "book": "📚 Kitob",
    "other": "📦 Boshqa",
}

PLACES: dict[str, str] = {
    "main_building": "🏛 Bosh bino",
    "fmf": "🏢 FMF binosi",
    "library": "📖 Kutubxona",
    "canteen": "🍽 Oshxona",
    "dormitory": "🏠 Yotoqxona",
    "gym": "🏋️ Sport zali",
    "other": "📍 Boshqa joy",
}

# E'lon turlari va holatlari
KIND_TITLES = {
    "lost": "🔴 YO'QOLGAN",
    "found": "🟢 TOPILGAN",
}
KIND_SHORT = {
    "lost": "🔴",
    "found": "🟢",
}
STATUS_TITLES = {
    "active": "🟡 Faol",
    "returned": "✅ Egasiga qaytarildi",
    "cancelled": "🚫 Bekor qilingan",
}

# ---------------------------------------------------------------------------
# /start, yordam va umumiy xabarlar
# ---------------------------------------------------------------------------
WELCOME = (
    "Assalomu alaykum, <b>{name}</b>! 👋\n\n"
    "<b>TOPDIM</b> — Urganch davlat universiteti talabalari uchun "
    "yo'qolgan va topilgan buyumlar boti.\n\n"
    "Buyumingiz yo'qoldimi yoki biror narsa topdingizmi? "
    "Quyidagi tugmalardan birini tanlang 👇"
)

MAIN_MENU = "Asosiy menyu 👇"

HELP = (
    "<b>TOPDIM botidan foydalanish</b>\n\n"
    f"<b>{BTN_LOST}</b> — yo'qotgan buyumingiz haqida e'lon bering.\n"
    f"<b>{BTN_FOUND}</b> — topgan buyumingiz haqida e'lon bering.\n"
    f"<b>{BTN_SEARCH}</b> — e'lonlarni kategoriya va kalit so'z bo'yicha qidiring.\n"
    f"<b>{BTN_MY_ITEMS}</b> — o'z e'lonlaringizni ko'ring, buyum qaytarilganda "
    "uni «Qaytarildi» deb belgilang yoki e'lonni bekor qiling.\n\n"
    "🔒 <b>Maxfiylik:</b> bot telefon raqamingizni so'ramaydi va hech kimga "
    "ko'rsatmaydi. E'longa telefon yoki karta raqamini yozmang.\n\n"
    f"Istalgan vaqtda <b>{BTN_CANCEL}</b> tugmasi yoki /start buyrug'i "
    "bilan asosiy menyuga qaytishingiz mumkin."
)

CANCELLED = "Amal bekor qilindi."
UNKNOWN_INPUT = "Tushunmadim 🤔 Iltimos, menyudagi tugmalardan foydalaning."
CHOOSE_FROM_BUTTONS = "Iltimos, tugmalardan birini tanlang 👇"
SEND_TEXT_PLEASE = "Iltimos, javobni matn ko'rinishida yuboring."

# ---------------------------------------------------------------------------
# E'lon berish (FSM) bosqichlari
# ---------------------------------------------------------------------------
ASK_CATEGORY = {
    "lost": "Nima yo'qoldi? Kategoriyani tanlang 👇",
    "found": "Nima topdingiz? Kategoriyani tanlang 👇",
}
ASK_TITLE = (
    "Buyum nomini qisqa yozing.\n"
    "<i>Masalan: «Qora charm hamyon» yoki «Samsung A52 telefoni»</i>"
)
ASK_PLACE = {
    "lost": "Buyumni qayerda yo'qotdingiz? 👇",
    "found": "Buyumni qayerda topdingiz? 👇",
}
ASK_PLACE_CUSTOM = "Joyni qisqacha yozing.\n<i>Masalan: «Avtobus bekati» yoki «2-qavat, 214-xona»</i>"
ASK_DATE = {
    "lost": "Buyum qachon yo'qoldi? 👇",
    "found": "Buyumni qachon topdingiz? 👇",
}
ASK_DATE_CUSTOM = "Sanani <b>KK.OO.YYYY</b> ko'rinishida yozing.\n<i>Masalan: 05.10.2026</i>"
ASK_DESCRIPTION = (
    "Buyumni batafsilroq tasvirlab bering: rangi, o'lchami, o'ziga xos belgilari.\n\n"
    "⚠️ Telefon raqami, karta raqami kabi shaxsiy ma'lumotlarni yozmang."
)
ASK_PHOTO = "Buyum rasmini yuboring (ixtiyoriy) yoki «O'tkazib yuborish» tugmasini bosing."
ASK_CONFIRM = "E'lon shunday ko'rinadi. Hammasi to'g'rimi?"

TEXT_TOO_SHORT = "Juda qisqa. Kamida {min} ta belgi yozing."
TEXT_TOO_LONG = "Juda uzun. Ko'pi bilan {max} ta belgi yozing (hozir: {length})."
CONTAINS_PHONE = (
    "🔒 Matnda telefon yoki karta raqamiga o'xshash ma'lumot bor. "
    "Xavfsizlik uchun uni olib tashlab, qaytadan yozing."
)

DATE_BAD_FORMAT = "Sana noto'g'ri. Iltimos, <b>KK.OO.YYYY</b> ko'rinishida yozing (masalan, 05.10.2026)."
DATE_IN_FUTURE = "Bu sana hali kelmagan 🙂 Bugungi yoki o'tgan sanani kiriting."
DATE_TOO_OLD = "Sana juda eski. Oxirgi {days} kun ichidagi sanani kiriting."

PHOTO_EXPECTED = "Iltimos, rasm yuboring yoki «O'tkazib yuborish» tugmasini bosing."

ITEM_CREATED = (
    "✅ E'loningiz joylandi! Raqami: <b>#{item_id}</b>\n\n"
    f"Uni «{BTN_MY_ITEMS}» bo'limida boshqarishingiz mumkin."
)

# ---------------------------------------------------------------------------
# E'lon kartochkasi
# ---------------------------------------------------------------------------
CARD_ID = " · #{item_id}"
CARD_TITLE = "📦 <b>{title}</b>"
CARD_CATEGORY = "🗂 Kategoriya: {category}"
CARD_PLACE = "📍 Joy: {place}"
CARD_DATE = {
    "lost": "📅 Yo'qolgan sana: {date}",
    "found": "📅 Topilgan sana: {date}",
}
CARD_DESCRIPTION = "📝 Tavsif: {description}"
CARD_STATUS = "🔖 Holati: {status}"

# ---------------------------------------------------------------------------
# Qidiruv
# ---------------------------------------------------------------------------
SEARCH_ASK_CATEGORY = "Qaysi kategoriyada qidiramiz? 👇"
SEARCH_ASK_KEYWORD = (
    "Kalit so'zni yozing (masalan: «hamyon», «qora», «kalit»).\n"
    "Kategoriyadagi barcha e'lonlarni ko'rish uchun «O'tkazib yuborish»ni bosing."
)
SEARCH_KEYWORD_TOO_LONG = "Kalit so'z juda uzun. Qisqaroq yozing."
SEARCH_RESULTS_HEADER = "🔎 Topilgan e'lonlar: <b>{total}</b> ta (sahifa {page}/{pages})\n"
SEARCH_NOTHING_FOUND = (
    "Afsuski, hech narsa topilmadi 😕\n"
    "Boshqa kalit so'z yoki kategoriya bilan urinib ko'ring."
)
SEARCH_EXPIRED = "Qidiruv eskirgan. Iltimos, qaytadan qidiring."
RESULTS_HINT = "\nBatafsil ko'rish uchun e'lon raqamini bosing 👇"

# ---------------------------------------------------------------------------
# Mening e'lonlarim va e'lonni boshqarish
# ---------------------------------------------------------------------------
MY_ITEMS_HEADER = "📋 Sizning e'lonlaringiz: <b>{total}</b> ta (sahifa {page}/{pages})\n"
MY_ITEMS_EMPTY = (
    "Sizda hali e'lonlar yo'q.\n"
    f"E'lon berish uchun «{BTN_LOST}» yoki «{BTN_FOUND}» tugmasini bosing."
)

BTN_PREV = "⬅️ Oldingi"
BTN_NEXT = "Keyingi ➡️"
BTN_MARK_RETURNED = "✅ Qaytarildi"
BTN_CANCEL_ITEM = "🚫 E'lonni bekor qilish"
BTN_YES_RETURNED = "✅ Ha, qaytarildi"
BTN_YES_CANCEL = "🚫 Ha, bekor qilinsin"
BTN_NO = "↩️ Yo'q, orqaga"

CONFIRM_MARK_RETURNED = "Buyum haqiqatan egasiga qaytarildimi? E'lon yopiladi."
CONFIRM_CANCEL_ITEM = "E'lonni bekor qilmoqchimisiz? U qidiruvda ko'rinmay qoladi."
STATUS_UPDATED_RETURNED = "🎉 Ajoyib! E'lon «Qaytarildi» deb belgilandi."
STATUS_UPDATED_CANCELLED = "E'lon bekor qilindi."
ITEM_NOT_FOUND = "E'lon topilmadi yoki u endi mavjud emas."
ITEM_NOT_YOURS = "Bu amalni faqat e'lon egasi bajara oladi."
ITEM_NOT_ACTIVE = "Bu e'lon allaqachon yopilgan."

# ---------------------------------------------------------------------------
# Avtomatik moslashtirish (2-bosqich)
# ---------------------------------------------------------------------------
MATCH_FOUND_FOR_NEW = (
    "🔔 <b>Sizning e'loningizga o'xshash e'lon topildi!</b>\n\n"
    "Sizning e'loningiz: <b>#{own_id}</b> {own_title}\n"
    "O'xshash e'lonlar soni: <b>{count}</b> ta\n\n"
    "Ko'rish uchun tugmani bosing 👇"
)
MATCH_FOUND_FOR_EXISTING = (
    "🔔 <b>Sizning e'loningizga o'xshash e'lon topildi!</b>\n\n"
    "Sizning e'loningiz: <b>#{own_id}</b> {own_title}\n"
    "Yangi e'lon: <b>#{other_id}</b> {other_title}\n\n"
    "Ko'rish uchun tugmani bosing 👇"
)
BTN_VIEW = "👀 Ko'rish"
BTN_VIEW_ITEM = "👀 Ko'rish #{item_id}"

# ---------------------------------------------------------------------------
# Mobil ilovaga kirish
# ---------------------------------------------------------------------------
APP_LOGIN_ASK = (
    "📱 <b>TOPDIM ilovasiga kirish</b>\n\n"
    "Telefoningizdagi TOPDIM ilovasiga shu Telegram akkaunt bilan kirmoqchimisiz?\n\n"
    "⚠️ Agar bu havolani o'zingiz ochmagan bo'lsangiz, tasdiqlamang."
)
BTN_APP_LOGIN_CONFIRM = "✅ Ha, kirish"
APP_LOGIN_DONE = "✅ Tayyor! Endi ilovaga qayting — u avtomatik ravishda kiradi."
APP_LOGIN_EXPIRED = "Bu kirish havolasi eskirgan. Ilovada «Telegram orqali kirish» tugmasini qaytadan bosing."

# API xatolari (mobil ilovada ko'rsatiladi)
API_LOGIN_REQUIRED = "Avval Telegram orqali kiring."
API_BAD_REQUEST = "So'rov noto'g'ri."
API_FIELD_REQUIRED = "«{field}» maydonini to'ldiring."
API_UNKNOWN_CHOICE = "«{field}» uchun noto'g'ri qiymat."
API_PLACE_NOTE_REQUIRED = "«Boshqa joy» tanlangan bo'lsa, joyni yozing."

# ---------------------------------------------------------------------------
# Bot buyruqlari (Telegram menyusida ko'rinadi)
# ---------------------------------------------------------------------------
COMMANDS = {
    "start": "Asosiy menyu",
    "help": "Yordam",
}
