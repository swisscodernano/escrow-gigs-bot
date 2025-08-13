import sys
import os
import asyncio

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.telegram_bot import main

if __name__ == "__main__":
    asyncio.run(main())