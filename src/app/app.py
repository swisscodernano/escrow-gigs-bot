from fastapi import FastAPI, Response
from app.telegram_bot import run_bot_background
import asyncio
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

@app.get("/health")
def health_get():
    return {"status": "ok"}

@app.head("/health")
def health_head():
    return Response(status_code=200)

@app.on_event("startup")
async def startup():
    asyncio.create_task(run_bot_background())
