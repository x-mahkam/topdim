"""Ilovaning barcha matnlari (o'zbek tili, lotin yozuvi).

Kategoriya va joy nomlari bu yerda emas — ular serverdan (/api/meta)
olinadi, shunda bot va ilovada har doim bir xil bo'ladi.
"""

APP_TITLE = "TOPDIM"

# Pastki menyu
TAB_FEED = "E'lonlar"
TAB_NEW = "E'lon berish"
TAB_MY = "Mening"
TAB_PROFILE = "Profil"

KIND_LABELS = {"lost": "Yo'qolgan", "found": "Topilgan"}
STATUS_LABELS = {"active": "Faol", "returned": "Egasiga qaytarildi", "cancelled": "Bekor qilingan"}

# E'lonlar ro'yxati
SEARCH_HINT = "Qidirish: hamyon, kalit, kutubxona…"
ALL_CATEGORIES = "Barcha kategoriyalar"
LOAD_MORE = "Yana ko'rsatish"
NOTHING_FOUND = "Hech narsa topilmadi 😕"
FOUND_COUNT = "Topildi: {total} ta"

# E'lon tafsiloti
DETAIL_CATEGORY = "Kategoriya"
DETAIL_PLACE = "Joy"
DETAIL_DATE = {"lost": "Yo'qolgan sana", "found": "Topilgan sana"}
DETAIL_DESCRIPTION = "Tavsif"
DETAIL_STATUS = "Holati"
CLOSE = "Yopish"
MARK_RETURNED = "Qaytarildi"
CANCEL_ITEM = "Bekor qilish"
CONFIRM_RETURNED = "Buyum haqiqatan egasiga qaytarildimi? E'lon yopiladi."
CONFIRM_CANCEL = "E'lonni bekor qilmoqchimisiz? U qidiruvda ko'rinmay qoladi."
YES = "Ha"
NO = "Yo'q"
STATUS_CHANGED = "E'lon holati yangilandi ✅"
CONTACT_HINT = (
    "Aloqa bot orqali bo'ladi: o'xshash e'lon topilsa, Telegram'da xabar olasiz."
)

# Yangi e'lon
NEW_TITLE = "Yangi e'lon"
FIELD_KIND = "Turi"
FIELD_CATEGORY = "Kategoriya"
FIELD_TITLE = "Buyum nomi"
FIELD_TITLE_HINT = "Masalan: Qora charm hamyon"
FIELD_PLACE = "Joy"
FIELD_PLACE_NOTE = "Joyni yozing"
FIELD_PLACE_NOTE_HINT = "Masalan: Avtobus bekati"
FIELD_DATE = "Sana"
DATE_TODAY = "Bugun"
DATE_YESTERDAY = "Kecha"
DATE_OTHER = "Boshqa sana"
FIELD_DESCRIPTION = "Tavsif"
FIELD_DESCRIPTION_HINT = "Rangi, o'lchami, o'ziga xos belgilari"
PRIVACY_NOTE = "Telefon yoki karta raqamini yozmang — aloqa bot orqali bo'ladi."
SUBMIT = "E'lonni joylash"
CHOOSE_CATEGORY = "Kategoriyani tanlang"
CHOOSE_PLACE = "Joyni tanlang"
ITEM_CREATED = "E'lon joylandi! Raqami: #{id}"

# Mening e'lonlarim
MY_TITLE = "Mening e'lonlarim"
MY_EMPTY = "Sizda hali e'lonlar yo'q."

# Kirish va profil
LOGIN_REQUIRED = "Bu bo'lim uchun Telegram orqali kiring."
LOGIN_BUTTON = "Telegram orqali kirish"
LOGIN_WAITING_TITLE = "Telegram'da tasdiqlang"
LOGIN_WAITING = (
    "Telegram ochildi. Botda «Start», keyin «✅ Ha, kirish» tugmasini bosing.\n\n"
    "Tasdiqlaganingizdan so'ng shu yerga qayting — ilova o'zi kiradi."
)
LOGIN_OPEN_AGAIN = "Telegram'ni qayta ochish"
LOGIN_SUCCESS = "Xush kelibsiz! ✅"
LOGIN_EXPIRED = "Kirish vaqti tugadi. Qaytadan urinib ko'ring."
LOGGED_IN = "Siz Telegram orqali kirgansiz."
LOGOUT = "Chiqish"
LOGGED_OUT = "Hisobdan chiqdingiz."

SERVER_TITLE = "Server manzili"
SERVER_HINT = "Masalan: 192.168.1.5:8080"
SERVER_HELP = (
    "Bot ishlayotgan kompyuterning manzili. Kompyuter va telefon bitta Wi-Fi'da "
    "bo'lsa, kompyuterning IP manzilini va 8080 portni yozing."
)
SERVER_SAVE = "Saqlash va tekshirish"
SERVER_OK = "Server bilan aloqa bor ✅ (@{bot})"
SERVER_REQUIRED = "Avval «Profil» bo'limida server manzilini kiriting."

ABOUT = "TOPDIM — UrDU talabalari uchun yo'qolgan va topilgan buyumlar xizmati."
CANCEL = "Bekor qilish"
LOADING = "Yuklanmoqda…"
