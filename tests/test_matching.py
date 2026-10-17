"""services/matching.py uchun testlar."""

from dataclasses import replace
from datetime import date, datetime, timezone

import pytest

from topdim.db.models import Item, ItemKind, ItemStatus
from topdim.services import matching
from topdim.services.matching import (
    MATCH_THRESHOLD,
    find_matches,
    keyword_overlap,
    score_match,
    title_keywords,
    words_match,
)

DAY = date(2026, 10, 10)


def make_item(item_id: int, kind: ItemKind, **overrides) -> Item:
    values = dict(
        id=item_id,
        kind=kind,
        owner_id=item_id * 10,
        category="bag",
        title="Qora charm hamyon",
        place="library",
        place_note=None,
        event_date=DAY,
        description="Tavsif",
        photo_file_id=None,
        status=ItemStatus.ACTIVE,
        created_at=datetime(2026, 10, 10, tzinfo=timezone.utc),
    )
    values.update(overrides)
    return Item(**values)


LOST = make_item(1, ItemKind.LOST)


# --- so'zlar ----------------------------------------------------------------
@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("kalit", "kalit", True),
        ("kalit", "kalitlar", True),   # qo'shimcha bilan
        ("hamyon", "hamyonim", True),
        ("bekati", "bekatda", True),    # umumiy o'zak "bekat"
        ("uy", "uyda", False),          # juda qisqa o'zak — tasodifiy moslik bo'lmasin
        ("telefon", "televizor", False),
        ("kitob", "kalit", False),
    ],
)
def test_words_match(a, b, expected):
    assert words_match(a, b) is expected


def test_title_keywords_drop_stopwords():
    assert title_keywords("Qora va katta HAMYON") == ["qora", "hamyon"]


def test_keyword_overlap_relative_to_shorter_title():
    assert keyword_overlap(["hamyon"], ["qora", "charm", "hamyon"]) == 1.0
    assert keyword_overlap(["qora", "sumka"], ["qora", "hamyon"]) == 0.5
    assert keyword_overlap([], ["hamyon"]) == 0.0


# --- ball -------------------------------------------------------------------
def test_identical_items_get_full_score():
    found = make_item(2, ItemKind.FOUND)
    result = score_match(LOST, found)
    assert result.score == 100
    assert result.reasons == {"category": 30, "keywords": 40, "place": 15, "date": 15}


@pytest.mark.parametrize(("days", "points"), [(0, 15), (1, 15), (3, 10), (7, 5), (14, 5)])
def test_date_points(days, points):
    found = make_item(2, ItemKind.FOUND, event_date=date.fromordinal(DAY.toordinal() + days))
    assert score_match(LOST, found).reasons["date"] == points


def test_more_than_14_days_apart_is_never_a_match():
    found = make_item(2, ItemKind.FOUND, event_date=date(2026, 10, 25))
    assert score_match(LOST, found).score == 0


def test_other_place_compares_written_notes():
    a = replace(LOST, place="other", place_note="Avtobus bekati")
    same = make_item(2, ItemKind.FOUND, place="other", place_note="bekatda")
    different = make_item(3, ItemKind.FOUND, place="other", place_note="Bozor")
    assert "place" in score_match(a, same).reasons
    assert "place" not in score_match(a, different).reasons


def test_different_category_but_same_name_can_still_match():
    # Foydalanuvchi boshqa kategoriya tanlagan bo'lishi mumkin
    found = make_item(2, ItemKind.FOUND, category="other", title="Hamyon")
    assert score_match(LOST, found).score >= MATCH_THRESHOLD


def test_unrelated_items_do_not_match():
    found = make_item(2, ItemKind.FOUND, category="book", title="Fizika darsligi", place="gym",
                      event_date=date(2026, 10, 20))
    assert score_match(LOST, found).score < MATCH_THRESHOLD


# --- find_matches -----------------------------------------------------------
def test_find_matches_filters_and_sorts():
    best = make_item(2, ItemKind.FOUND)
    good = make_item(3, ItemKind.FOUND, title="Hamyon", place="canteen")
    weak = make_item(4, ItemKind.FOUND, category="book", title="Kitob", place="gym")
    same_kind = make_item(5, ItemKind.LOST)
    own = make_item(6, ItemKind.FOUND, owner_id=LOST.owner_id)
    closed = make_item(7, ItemKind.FOUND, status=ItemStatus.RETURNED)

    results = find_matches(LOST, [weak, good, same_kind, own, closed, best])
    assert [r.item.id for r in results] == [2, 3]
    assert results[0].score > results[1].score


def test_find_matches_respects_limit_and_threshold():
    candidates = [make_item(i, ItemKind.FOUND) for i in range(2, 12)]
    assert len(find_matches(LOST, candidates, limit=3)) == 3
    assert find_matches(LOST, candidates, threshold=101) == []


def test_opposite_kind():
    assert matching.opposite_kind(ItemKind.LOST) is ItemKind.FOUND
    assert matching.opposite_kind(ItemKind.FOUND) is ItemKind.LOST
