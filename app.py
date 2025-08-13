import asyncio
import logging
from fastapi import FastAPI

# Import the bot runner with a Docker/local fallback
try:
    from app._autostart import run_bot_background  # when running inside the container (package path)
except Exception:
    from _autostart import run_bot_background      # when running locally from repo root

app = FastAPI()

@app.get("/")
def root():
    return {"ok": True, "service": "escrow-gigs-bot"}

@app.on_event("startup")
async def startup():
    # start telegram bot in background (if TELEGRAM_TOKEN is set)
    try:
        task = asyncio.create_task(run_bot_background())
        # keep a ref so GC doesn't kill it
        app.state.bot_task = task
        logging.info("Bot background task scheduled.")
    except Exception as e:
        logging.exception("Failed to schedule bot background task: %s", e)
