# TOPDIM

Urganch davlat universiteti (UrDU) talabalari uchun **yo'qolgan va topilgan
buyumlar** Telegram boti. Buyumini yo'qotgan talaba e'lon beradi, buyum topgan
talaba ham e'lon beradi, bot esa ularni bir-biriga topishtirishga yordam beradi.

> 🔒 Bot telefon raqamini so'ramaydi va hech qachon ko'rsatmaydi. E'lonlarda
> e'lon egasining ismi yoki username'i ham chiqmaydi.

## Loyiha tarixi

G'oya talaba yozgan konsol dasturidan boshlangan: `legacy/Topdim.py`. U
e'lonlarni `elonlar.json` faylida saqlaydi va menyu orqali e'lon berish,
qidirish va o'chirish imkonini beradi. Bot shu g'oyani davom ettiradi;
dastlabki kod o'rganish uchun o'zgartirilmasdan saqlangan.

## Imkoniyatlar

Loyiha bosqichma-bosqich quriladi.

- [x] **1-bosqich — asosiy e'lonlar**
  - «Buyumim yo'qoldi» / «Buyum topdim»: kategoriya → nom → joy → sana →
    tavsif → rasm (ixtiyoriy) → tasdiqlash;
  - kalit so'z va kategoriya bo'yicha qidiruv, natijalar 5 tadan sahifalarda;
  - «Mening e'lonlarim»: e'lonni «Qaytarildi» deb belgilash yoki bekor qilish
    (e'lonlar o'chirilmaydi, faqat holati o'zgaradi);
  - tavsifga telefon yoki karta raqami yozilsa, bot uni qabul qilmaydi.
- [x] **2-bosqich — o'xshash e'lonlarni avtomatik topish**
  - yangi e'lon qo'shilganda qarama-qarshi turdagi faol e'lonlar bilan
    solishtiriladi va ball qo'yiladi (pastdagi jadvalga qarang);
  - ball chegaradan (50) oshsa, ikkala e'lon egasiga «👀 Ko'rish» tugmali
    xabar boradi; bir juftlik haqida xabar faqat bir marta yuboriladi.
- [ ] 3-bosqich — anonim aloqa va egalikni tekshirish
- [ ] 4-bosqich — QR-yorliq
- [ ] 5-bosqich — admin paneli va statistika

## O'rnatish

Kerak bo'ladi: **Python 3.11** yoki undan yangi versiya.

```bash
# 1. Repozitoriyani yuklab oling
git clone https://github.com/x-mahkam/topdim.git
cd topdim

# 2. Virtual muhit yarating va faollashtiring
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Kutubxonalarni o'rnating
pip install -r requirements.txt
# testlarni ham ishga tushirmoqchi bo'lsangiz:
pip install -r requirements-dev.txt
```

## .env faylini sozlash

1. Telegram'da [@BotFather](https://t.me/BotFather) ga `/newbot` yozing va
   yangi bot yarating. U sizga **token** beradi.
2. Namunadan nusxa oling:

   ```bash
   cp .env.example .env            # Windows: copy .env.example .env
   ```

3. `.env` faylini oching va qiymatlarni yozing:

   | O'zgaruvchi | Tavsif |
   |-------------|--------|
   | `BOT_TOKEN` | @BotFather bergan token (majburiy) |
   | `ADMIN_IDS` | adminlarning Telegram ID'lari, vergul bilan (masalan `111,222`). O'z ID'ingizni [@userinfobot](https://t.me/userinfobot) orqali bilib olasiz |
   | `DB_PATH`   | SQLite baza fayli nomi (ixtiyoriy, standart: `topdim.db`) |

> ⚠️ `.env` fayl `.gitignore`'ga qo'shilgan — uni hech qachon GitHub'ga
> yuklamang. Token boshqa odam qo'liga tushsa, @BotFather'da `/revoke` qiling.

## Botni ishga tushirish

Loyihaning ildiz papkasida (`README.md` turgan joyda):

```bash
python -m topdim.bot
```

Konsolda `Bot ishga tushdi: @...` yozuvi chiqsa, Telegram'da botingizga
`/start` yozing. To'xtatish uchun `Ctrl+C` bosing. Ma'lumotlar bazasi fayli
birinchi ishga tushganda avtomatik yaratiladi.

## Testlar

```bash
pytest
```

Testlar internet va haqiqiy token talab qilmaydi: `tests/test_bot_flow.py`
Telegram o'rniga soxta sessiyadan foydalanadi va botning to'liq ish
jarayonini (e'lon berish, qidiruv, holatni o'zgartirish) tekshiradi.

## Loyiha tuzilmasi

```
topdim/
  bot.py              — ishga tushirish nuqtasi: bot, dispatcher, routerlar
  config.py           — .env dan sozlamalarni o'qish
  db/
    database.py       — SQLite ulanishi va jadvallar (yupqa qatlam)
    models.py         — Item, ItemKind, ItemStatus
    queries.py        — barcha SQL so'rovlar
  handlers/           — har bir bo'lim alohida router
    common.py         — /start, /help, «Bekor qilish»
    new_item.py       — e'lon berish (FSM)
    search.py         — qidiruv
    my_items.py       — «Mening e'lonlarim»
    items.py          — e'lonni ko'rish, «Qaytarildi» / bekor qilish
    fallback.py       — tushunarsiz xabarlar
    utils.py          — umumiy yordamchi funksiyalar
  keyboards/
    reply.py          — pastki (reply) tugmalar
    inline.py         — xabar ostidagi (inline) tugmalar va callback_data
  services/           — Telegram'ga bog'liq bo'lmagan logika
    cards.py          — e'lon kartochkasi matni
    matching.py       — o'xshash e'lonlarni topish (ball hisoblash)
    notifications.py  — moslik haqida xabar yuborish
    dates.py          — sanani tekshirish va formatlash
    pagination.py     — sahifalash
    privacy.py        — telefon/karta raqamini aniqlash
    text.py           — matnni normallashtirish, kalit so'zlar
  locales/uz.py       — botning barcha matnlari
tests/                — pytest testlari
legacy/Topdim.py      — botning asosi bo'lgan dastlabki konsol dasturi
```

### Avtomatik moslashtirish qanday ishlaydi

`services/matching.py` ikki e'lonni 0–100 ball bilan baholaydi:

| Mezon | Ball |
|-------|------|
| Kategoriya bir xil | 30 |
| Nomdagi so'zlar mos kelishi | 0–40 (umumiy so'zlar ulushiga qarab) |
| Joy bir xil | 15 |
| Sana farqi | ≤1 kun: 15, ≤3 kun: 10, ≤14 kun: 5 |

- Sana farqi 14 kundan oshsa, e'lonlar solishtirilmaydi.
- So'zlar o'zagi bo'yicha solishtiriladi: «kalit» va «kalitlar», «bekati» va
  «bekatda» mos deb hisoblanadi.
- Faqat qarama-qarshi turdagi (yo'qolgan ↔ topilgan), faol va boshqa odamga
  tegishli e'lonlar solishtiriladi.
- Ballar va chegara (`MATCH_THRESHOLD`) fayl boshida konstanta sifatida
  berilgan — ularni o'zgartirib tajriba qilib ko'ring va `pytest
  tests/test_matching.py` bilan tekshiring.

### Qanday ishlaydi (talabalar uchun qisqacha)

- **Router** — handlerlar guruhi. `handlers/__init__.py` ularni tartib bilan
  ulaydi: avval umumiy buyruqlar, oxirida «tushunmadim» javobi.
- **FSM** (chekli holatlar mashinasi) — bot foydalanuvchi qaysi savolga javob
  berayotganini eslab qoladi. `handlers/new_item.py`dagi `NewItemForm`ga qarang.
- **Handlerlar bazaga to'g'ridan-to'g'ri SQL yozmaydi** — faqat
  `db/queries.py` funksiyalarini chaqiradi. PostgreSQL'ga o'tishda asosan
  `db/database.py` va `db/queries.py` o'zgaradi.
- **Barcha matnlar `locales/uz.py`da.** Tugma matnini o'zgartirsangiz, uni
  qabul qiluvchi handler ham avtomatik moslashadi.
- **services/** dagi funksiyalar Telegram'siz ishlaydi, shuning uchun ularni
  test qilish oson.
