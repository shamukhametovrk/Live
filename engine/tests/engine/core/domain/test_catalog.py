"""Справочник предметов не расходится с правилами в docs/rules/items/."""

import re
from pathlib import Path

from engine.core.domain.catalog import CATALOG, Item, ItemClass

ITEMS_DOCS = Path(__file__).parents[5] / "docs" / "rules" / "items"

DOC_CLASS = {
    "common": ItemClass.COMMON,
    "rare": ItemClass.RARE,
    "ceiling": ItemClass.CEILING,
}


def doc_class(item: Item) -> ItemClass:
    text = (ITEMS_DOCS / f"{item.value}.md").read_text(encoding="utf-8")
    found = re.search(r'class="cls cls--(\w+)"', text)
    assert found, f"no class on page {item.value}"
    return DOC_CLASS[found.group(1)]


def test_every_item_page_has_an_item_and_back():
    pages = {p.stem for p in ITEMS_DOCS.glob("*.md")} - {"index"}
    assert pages == {item.value for item in Item}
    assert set(CATALOG) == set(Item)


def test_item_classes_match_rules():
    assert {i: CATALOG[i].cls for i in Item} == {i: doc_class(i) for i in Item}
