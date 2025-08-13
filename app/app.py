import asyncio, logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app._autostart import run_bot_background
from app.api.webhooks import router as webhooks_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    try:
        @app.on_event("startup")
async def startup_event():
    # You can add any startup logic here if needed
    pass
        logging.info("Bot task scheduled.")
    except Exception as e:
        logging.exception("Bot not started: %s", e)
    yield
    # shutdown
    task = getattr(app.state, "bot_task", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

app = FastAPI(lifespan=lifespan)

app.include_router(webhooks_router)

@app.get("/")
def root():
    return {"ok": True, "service": "escrow-gigs-bot"}
