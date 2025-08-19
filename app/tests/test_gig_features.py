import sys
sys.path.insert(0, 'src')
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import quote

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.models import Base, Gig, User
from app.telegram_bot import (
    cmd_categories,
    category_gigs,
    cmd_search,
    search_gigs_paginated,
    CATEGORIES,
    PAGE_SIZE,
)


@pytest.fixture
def sessionmaker_():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Add a dummy user
    seller = User(tg_id="123", username="testseller")
    db.add(seller)
    db.commit()
    db.refresh(seller)

    # Add some dummy gigs
    gigs_data = [
        {
            "seller_id": seller.id,
            "title": "Gig 1",
            "description": "Description 1",
            "price_usd": 10.0,
            "category": "Web Development",
        },
        {
            "seller_id": seller.id,
            "title": "Gig 2",
            "description": "Description 2",
            "price_usd": 20.0,
            "category": "Web Development",
        },
        {
            "seller_id": seller.id,
            "title": "Gig 3",
            "description": "Description 3",
            "price_usd": 30.0,
            "category": "Writing",
        },
    ]
    # Add gigs for search testing
    for i in range(12):
        gigs_data.append(
            {
                "seller_id": seller.id,
                "title": f"Searchable Gig {i}",
                "description": "A very specific keyword",
                "price_usd": i,
                "category": "Other",
            }
        )
    for gig_data in gigs_data:
        db.add(Gig(**gig_data))
    db.commit()
    db.close()
    return Session

@pytest.mark.asyncio
async def test_cmd_categories(monkeypatch, sessionmaker_):
    """Test the /categories command."""
    update = AsyncMock()
    context = MagicMock()

    # Mock db_session
    monkeypatch.setattr("app.telegram_bot.db_session", sessionmaker_)

    await cmd_categories(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert call_args.args[0] == "Please choose a category:"

    # Check the buttons
    reply_markup = call_args.kwargs["reply_markup"]
    assert len(reply_markup.inline_keyboard) == len(CATEGORIES)
    for i, category in enumerate(CATEGORIES):
        button = reply_markup.inline_keyboard[i][0]
        assert button.text == category
        assert button.callback_data == f"category_{quote(category)}_page_1"


@pytest.mark.asyncio
async def test_category_gigs_pagination(monkeypatch, sessionmaker_):
    """Test the category_gigs command with pagination."""
    update = AsyncMock()
    context = MagicMock()

    # Mock db_session
    monkeypatch.setattr("app.telegram_bot.db_session", sessionmaker_)

    # Simulate a callback query
    category = "Web Development"
    page = 1
    update.callback_query.data = f"category_{quote(category)}_page_{page}"

    await category_gigs(update, context)

    update.callback_query.answer.assert_called_once()
    update.callback_query.edit_message_text.assert_called_once()

    call_args = update.callback_query.edit_message_text.call_args

    # Check the text
    text = call_args.args[0]
    assert f"Gigs in {category}" in text
    assert "Gig 1" in text
    assert "Gig 2" in text
    assert "Gig 3" not in text  # Belongs to another category

    # Check the pagination buttons
    reply_markup = call_args.kwargs["reply_markup"]
    # In this test case, there are only 2 gigs in Web Development, and PAGE_SIZE is 5,
    # so there should be no pagination buttons.
    assert not reply_markup.inline_keyboard

    # --- Test with more data to force pagination ---
    db = sessionmaker_()
    seller_id = db.query(User).first().id
    for i in range(PAGE_SIZE):
        db.add(
            Gig(
                seller_id=seller_id,
                title=f"WD Gig {i}",
                description="...",
                price_usd=1,
                category="Web Development",
            )
        )
    db.commit()
    db.close()

    # Test page 1
    update.reset_mock()
    page = 1
    update.callback_query.data = f"category_{quote(category)}_page_{page}"
    await category_gigs(update, context)
    update.callback_query.edit_message_text.assert_called_once()
    call_args = update.callback_query.edit_message_text.call_args
    reply_markup = call_args.kwargs["reply_markup"]
    assert len(reply_markup.inline_keyboard) == 1
    assert reply_markup.inline_keyboard[0][0].text == "Next ➡️"

    # Test page 2
    update.reset_mock()
    page = 2
    update.callback_query.data = f"category_{quote(category)}_page_{page}"
    await category_gigs(update, context)
    update.callback_query.edit_message_text.assert_called_once()
    call_args = update.callback_query.edit_message_text.call_args
    reply_markup = call_args.kwargs["reply_markup"]
    assert len(reply_markup.inline_keyboard) == 1
    assert reply_markup.inline_keyboard[0][0].text == "⬅️ Prev"


@pytest.mark.asyncio
async def test_cmd_search_pagination(monkeypatch, sessionmaker_):
    """Test the /search command with pagination."""
    update = AsyncMock()
    context = MagicMock()

    # Mock db_session
    monkeypatch.setattr("app.telegram_bot.db_session", sessionmaker_)

    # Simulate a search command
    keyword = "specific keyword"
    update.message.text = f"/search {keyword}"
    context.args = [keyword]

    await cmd_search(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args.args[0]

    assert f"Search results for '{keyword}'" in text
    assert "Searchable Gig 11" in text
    assert "Searchable Gig 7" in text
    assert "Searchable Gig 6" not in text

    reply_markup = call_args.kwargs["reply_markup"]
    assert len(reply_markup.inline_keyboard) == 1
    assert reply_markup.inline_keyboard[0][0].text == "Next ➡️"
    assert (
        reply_markup.inline_keyboard[0][0].callback_data
        == f"search_{quote(keyword)}_page_2"
    )


@pytest.mark.asyncio
async def test_search_gigs_paginated(monkeypatch, sessionmaker_):
    """Test the search_gigs_paginated command."""
    update = AsyncMock()
    context = MagicMock()

    # Mock db_session
    monkeypatch.setattr("app.telegram_bot.db_session", sessionmaker_)

    keyword = "specific keyword"

    # Test page 2
    update.reset_mock()
    page = 2
    update.callback_query.data = f"search_{quote(keyword)}_page_{page}"
    await search_gigs_paginated(update, context)
    update.callback_query.edit_message_text.assert_called_once()
    call_args = update.callback_query.edit_message_text.call_args
    text = call_args.args[0]

    assert "Searchable Gig 6" in text
    assert "Searchable Gig 2" in text
    assert "Searchable Gig 1" not in text

    reply_markup = call_args.kwargs["reply_markup"]
    assert len(reply_markup.inline_keyboard) == 1
    assert len(reply_markup.inline_keyboard[0]) == 2  # Prev and Next
    assert reply_markup.inline_keyboard[0][0].text == "⬅️ Prev"
    assert reply_markup.inline_keyboard[0][1].text == "Next ➡️"

    # Test page 3 (last page)
    update.reset_mock()
    page = 3
    update.callback_query.data = f"search_{quote(keyword)}_page_{page}"
    await search_gigs_paginated(update, context)
    update.callback_query.edit_message_text.assert_called_once()
    call_args = update.callback_query.edit_message_text.call_args
    text = call_args.args[0]

    assert "Searchable Gig 1" in text
    assert "Searchable Gig 0" in text
    assert "Searchable Gig 2" not in text

    reply_markup = call_args.kwargs["reply_markup"]
    assert len(reply_markup.inline_keyboard) == 1
    assert len(reply_markup.inline_keyboard[0]) == 1
    assert reply_markup.inline_keyboard[0][0].text == "⬅️ Prev"
