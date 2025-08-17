import sys
import os
import asyncio
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.telegram_bot import run_bot_background

if __name__ == "__main__":
    asyncio.run(run_bot_background())
    while True:
        time.sleep(1)

