import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.bot.main import bot_app

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the FastAPI application.
    """
    logger.info("Starting bot polling...")
    # Start the bot in the background
    await bot_app.initialize()
    await bot_app.start()

    # The bot runs in its own thread, so we can just yield
    yield

    # Stop the bot when the application shuts down
    logger.info("Stopping bot polling...")
    await bot_app.stop()
    await bot_app.shutdown()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    return {"status": "ok"}
