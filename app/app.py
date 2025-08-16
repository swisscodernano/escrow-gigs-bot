import asyncio

from dotenv import load_dotenv
from fastapi import FastAPI, Response

from app.telegram_bot import run_bot_background

load_dotenv()

fastapi_app = FastAPI()


@fastapi_app.get("/health")
def health_get():
    return {"status": "ok"}


@fastapi_app.head("/health")
def health_head():
    return Response(status_code=200)


@fastapi_app.on_event("startup")
async def startup():
    asyncio.create_task(run_bot_background())
