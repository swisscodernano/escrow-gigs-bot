from fastapi import FastAPI, Response
from app.telegram_bot import run_bot_background
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the bot on application startup
    bot_task = asyncio.create_task(run_bot_background())
    yield
    # Optional: Add cleanup logic here if the bot task needs to be cancelled
    # bot_task.cancel()

fastapi_app = FastAPI(lifespan=lifespan)

@fastapi_app.get("/health")
def health_get():
    return {"status": "ok"}

@fastapi_app.head("/health")
def health_head():
    return Response(status_code=200)