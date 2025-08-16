from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient

from app.app import fastapi_app
from app.telegram_bot import cmd_help, cmd_start


@pytest.mark.asyncio
async def test_start_command():
    update = MagicMock()
    update.effective_user.id = 12345
    update.effective_user.username = "testuser"
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    await cmd_start(update, context)
    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_help_command():
    update = MagicMock()
    update.effective_user.id = 12345
    update.effective_user.username = "testuser"
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    await cmd_help(update, context)
    update.message.reply_text.assert_called_once()


def test_health_check():
    client = TestClient(fastapi_app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
