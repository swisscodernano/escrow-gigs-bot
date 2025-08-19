# Codex Runbook for `escrow-gigs-bot`

This document explains how to run the project locally, how Codex is configured for this repo, and how to create good Codex tasks.

---

## 1) Tech overview

- **FastAPI** backend served by **uvicorn**
- **python-telegram-bot v20.x** for the Telegram bot
- `app/_autostart.py` bridges the bot into FastAPI startup, sets the command menu, and provides English UX prompts
- Core business logic for commands lives in **`app/telegram_bot.py`** (we call into those handlers from `_autostart.py`)

> Design rule: keep **all user‑facing strings in English** and **don’t change handler business logic** unless the task requires it.

---

## 2) Local setup

### Python & dependencies

1. Python 3.11 recommended.
2. Install pinned deps (pin is important for PTB 20.x):
   ```bash
   python -m pip install -U pip
   python -m pip install -r requirements.txt
