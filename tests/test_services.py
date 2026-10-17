"""services/ ichidagi sof funksiyalar uchun testlar."""

from datetime import date, datetime, timezone

import pytest

from topdim.db.models import Item, ItemKind, ItemStatus
from topdim.services.cards import format_card, format_item_card, format_item_line
from topdim.services.dates import DateInputError, format_date, parse_user_date
from topdim.services.pagination import make_page
from topdim.services.privacy import contains_phone_number
from topdim.services.text import extract_keywords, normalize

TODAY = date(2026, 10, 17)


# --- text -------------------------------------------------------------------
def test_normalize_unifies_apostrophes_and_case():
    assert normalize("  Oʻquv  ZALI ") == "o'quv zali"
    assert normalize("g‘ildirak o`yinchoq") == "g'ildirak o'yinchoq"


def test_extract_keywords_removes_duplicates_and_short_words():
    assert extract_keywords("Qora hamyon, QORA va 5 so'm") == ["qora", "hamyon", "va", "so'm"]
    assert extract_keywords("a ! ?") == []


# --- dates ------------------------------------------------------------------
@pytest.mark.parametrize("text", ["05.10.2026", "5.10.2026", "05/10/2026", " 05-10-2026 "])
def test_parse_user_date_accepts_common_formats(text):
    assert parse_user_date(text, TODAY) == date(2026, 10, 5)


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("kecha", "format"),
        ("2026-10-05", "format"),
        ("31.02.2026", "format"),
        ("18.10.2026", "future"),
        ("01.01.2025", "too_old"),
    ],
)
def test_parse_user_date_rejects_bad_dates(text, reason):
    with pytest.raises(DateInputError) as error:
        parse_user_date(text, TODAY)
    assert error.value.reason == reason


def test_format_date():
    assert format_date(date(2026, 3, 7)) == "07.03.2026"


# --- pagination -------------------------------------------------------------
def test_make_page_basic():
    page = make_page(total_items=12, requested=1)
    assert (page.number, page.total_pages, page.offset) == (1, 3, 5)
    assert page.has_prev and page.has_next


def test_make_page_clamps_out_of_range():
    assert make_page(12, 99).number == 2
    assert make_page(12, -3).number == 0
    empty = make_page(0, 0)
    assert empty.total_pages == 1 and not empty.has_next and not empty.has_prev


def test_make_page_exact_multiple():
    page = make_page(10, 1)
    assert page.total_pages == 2 and not page.has_next


# --- privacy ----------------------------------------------------------------
@pytest.mark.parametrize(
    "text",
    ["Tel: +998 90 123-45-67", "901234567 ga qo'ng'iroq", "karta 8600 1234 5678 9012", "(90) 123 45 67"],
)
def test_contains_phone_number_detects(text):
    assert contains_phone_number(text)


@pytest.mark.parametrize("text", ["Pasport AB1234567", "214-xona, 2-qavat", "iPhone 12 Pro", "2026 yil"])
def test_contains_phone_number_ignores_normal_text(text):
    assert not contains_phone_number(text)


# --- cards ------------------------------------------------------------------
def make_item(**overrides) -> Item:
    values = dict(
        id=7,
        kind=ItemKind.FOUND,
        owner_id=42,
        category="keys",
        title="Kalitlar <b>to'plami</b>",
        place="library",
        place_note=None,
        event_date=date(2026, 10, 5),
        description="Uchta kalit & brelok",
        photo_file_id=None,
        status=ItemStatus.ACTIVE,
        created_at=datetime(2026, 10, 5, tzinfo=timezone.utc),
    )
    values.update(overrides)
    return Item(**values)


def test_item_card_escapes_user_text_and_hides_owner():
    card = format_item_card(make_item())
    assert "&lt;b&gt;to'plami&lt;/b&gt;" in card
    assert "&amp; brelok" in card
    assert "#7" in card and "Kutubxona" in card and "05.10.2026" in card
    assert "42" not in card  # egasining ID'si ko'rinmaydi


def test_card_preview_without_id_and_status():
    card = format_card(
        kind="lost", category="bag", title="Hamyon", place="other", place_note="Bekat",
        event_date=date(2026, 10, 1), description="Jigarrang",
    )
    assert "#" not in card and "Holati" not in card
    assert "Bekat" in card and "YO'QOLGAN" in card


def test_item_line_truncates_long_titles():
    line = format_item_line(make_item(title="A" * 80), show_status=True)
    assert "…" in line and "Faol" in line
