# Task: Phase 1 - Foundation & API Setup

Hi Jules,

We are officially kicking off **Project Phoenix**, a complete rebuild of the Escrow Gigs Bot. We are starting fresh from a clean `new-main` branch to ensure stability, maintainability, and build a professional-grade application.

**The Goal:** Lay a Solid Foundation

Your first mission is to establish the project's core foundation. This phase is critical as it will underpin all future development. We need a robust, modern, and scalable structure.

**The Task: Build the Project Scaffolding and Core Services**

You are to build the initial structure of the FastAPI application, set up the database with Alembic for migrations, and implement a Pydantic-based configuration system.

**Key Requirements & Features to Implement:**

1.  **Project Scaffolding:**
    *   Initialize a modern Python project using a `pyproject.toml` file for dependency management.
    *   Create a logical `app` module with the following sub-directory structure:
        *   `app/api` (for API endpoints)
        *   `app/core` (for configuration and core logic)
        *   `app/db` (for database session management and migrations)
        *   `app/models` (for SQLAlchemy models)
        *   `app/services` (for business logic)
        *   `app/bot` (for all Telegram-related code)

2.  **Database & Migrations:**
    *   Integrate SQLAlchemy and configure it to connect to the PostgreSQL database.
    *   Set up Alembic to manage database migrations.
    *   Create the first model, `User`, in `app/models/user.py`. It must contain: `id` (PK), `tg_id` (string, unique), `username` (string), and `lang` (string, default 'en').
    *   Generate the initial Alembic migration for the `User` model.

3.  **Core Configuration & Health Check:**
    *   In `app/core/config.py`, create a `Settings` class using Pydantic to manage all environment variables (e.g., `DATABASE_URL`, `BOT_TOKEN`).
    *   Create a `.env.example` file in the root directory, listing all required variables.
    *   In `app/api/main.py`, create a simple `/health` endpoint that returns `{"status": "ok"}` to confirm the API is running.

**Our Workflow (Please follow this strictly):**

1.  **Development Environment:** You must use the Docker-based environment.
    *   Build: `docker-compose -f docker-compose.dev.yml build`
    *   Start: `docker-compose -f docker-compose.dev.yml up -d`
    *   Work inside: `docker-compose -f docker-compose.dev.yml exec dev bash`

2.  **Branching:** Create your feature branch from the `new-main` branch.
    *   `git checkout new-main`
    *   `git pull origin new-main`
    *   `git checkout -b feature/phase-1-foundation`

3.  **Code Quality:** Before each commit, please run the following tools:
    *   `black .`
    *   `isort .`
    *   `flake8 .`
    *   `mypy .`

4.  **Testing:** Run the test suite (even if it's empty initially) to ensure the setup is correct.
    *   `pytest`

5.  **Submission:** When you have completed all tasks in this phase, push your `feature/phase-1-foundation` branch to GitHub and open a Pull Request targeting `new-main`. I will review it. **Do not merge it yourself.**

This foundational work is the most important step. Let's get it right.

Let me know if you have any questions.

- Gemini
