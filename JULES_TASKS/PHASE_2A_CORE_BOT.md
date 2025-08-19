# Task: Phase 2A - Core Bot & i18n

Hi Jules,

With the project foundation in place, your next task is to build the core of the user-facing Telegram bot. This will run in parallel with the data modeling task.

**The Goal:** Create a functional, multilingual bot interface.

**The Task: Implement the Bot's Entry Points, Handlers, and Translation System**

You will initialize the `python-telegram-bot` application, set up the i18n system with `pybabel`, and create the initial user-facing commands.

**Key Requirements & Features to Implement:**

1.  **Bot Initialization:**
    *   In `app/bot/main.py`, write the logic to initialize the bot application.
    *   Ensure the bot is started from the FastAPI `lifespan` manager in `app/main.py`.
    *   The bot should fetch its token from the Pydantic `Settings` object.

2.  **Internationalization (i18n) System:**
    *   In `app/i18n/`, set up the directory structure for translations (`<lang>/LC_MESSAGES/`).
    *   Create a `translator.py` module. The `get_translation` function must use an **absolute path** to the `localedir` to prevent issues.
    *   Generate the `.pot` template and create `.po` files for English (`en`) and Italian (`it`).
    *   **Crucially, add a script or documented command to compile `.po` files to `.mo` files.**

3.  **Basic Command Handlers:**
    *   Implement the `/start` command. It should greet the user and display a main menu with inline buttons (e.g., "Create Gig," "My Orders"). All text must be translatable.
    *   Implement the `/lang` command. It should allow a user to switch their language. The chosen language must be saved to the `lang` column of the `User` model in the database.

**Workflow:**

1.  **Branching:** Create your feature branch from the latest `new-main`.
    *   `git checkout new-main && git pull`
    *   `git checkout -b feature/phase-2a-core-bot`
2.  **Code Quality & Testing:** Run `black`, `isort`, `flake8`, `mypy`, and `pytest` before committing.
3.  **Submission:** When complete, open a Pull Request to `new-main`.

- Gemini
