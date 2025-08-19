import asyncio
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from app.api.admin import admin_router  # Import the admin router
from app.telegram_bot import run_bot_background

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the bot on application startup
    asyncio.create_task(run_bot_background())
    yield
    # Optional: Add cleanup logic here if the bot task needs to be cancelled
    # bot_task.cancel()


fastapi_app = FastAPI(lifespan=lifespan)

# Mount static files and templates
fastapi_app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Include the admin router
fastapi_app.include_router(admin_router, prefix="/admin", tags=["admin"])


@fastapi_app.get("/health")
def health_get():
    return {"status": "ok"}


@fastapi_app.head("/health")
def health_head():
    return Response(status_code=200)
