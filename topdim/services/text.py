"""Matnni qidiruv uchun tayyorlash.

O'zbek lotin yozuvida tutuq belgisi har xil yoziladi: o', oʻ, o‘, o` ...
Qidiruv to'g'ri ishlashi uchun ularning hammasini bitta ko'rinishga keltiramiz.
"""

import re

# Barcha tutuq belgisi variantlari oddiy apostrofga almashtiriladi
_APOSTROPHES = str.maketrans({"ʻ": "'", "ʼ": "'", "‘": "'", "’": "'", "`": "'", "´": "'"})

# So'z: harflar, raqamlar va so'z ichidagi apostrof (masalan, "o'quv")
_WORD_RE = re.compile(r"\w+(?:'\w+)*")

MIN_KEYWORD_LENGTH = 2


def normalize(text: str) -> str:
    """Matnni kichik harfga o'tkazadi, tutuq belgilarini va bo'shliqlarni tekislaydi."""
    text = text.translate(_APOSTROPHES).lower()
    return " ".join(text.split())


def extract_keywords(text: str) -> list[str]:
    """Matndan kalit so'zlarni ajratadi (takrorlarsiz, tartib saqlanadi).

    >>> extract_keywords("Qora  HAMYON, qora")
    ['qora', 'hamyon']
    """
    words = _WORD_RE.findall(normalize(text))
    unique: list[str] = []
    for word in words:
        if len(word) >= MIN_KEYWORD_LENGTH and word not in unique:
            unique.append(word)
    return unique
