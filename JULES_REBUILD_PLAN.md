# Project Phoenix: Escrow Gigs Bot Rebuild Plan

## 1. Introduction

**Objective:** To rebuild the Escrow Gigs Bot from the ground up to ensure stability, maintainability, and a clean codebase. All previous branches will be archived for reference, and all new development will happen on this new `main` branch.

**Coordinator:** Gemini

**Lead Developer:** Jules

---

## 2. Instructions for Jules

-   **Branching:** Create a new feature branch for each `Phase` (e.g., `feature/phase-1-foundation`, `feature/phase-2-core-bot`).
-   **Commits:** Use clear, conventional commit messages (e.g., `feat: implement user model`, `fix: correct i18n path`).
-   **Pull Requests:** Once a phase is complete, open a Pull Request to the `new-main` branch. I (Gemini) will review it. Do not merge your own PRs.
-   **Communication:** All communication and documentation will be in English.

---

## 3. Phase 1: Foundation & API Setup

**Goal:** Establish a robust project structure with a functional FastAPI backend and database connectivity.

-   **Task 1.1: Project Scaffolding**
    -   Initialize a modern Python project structure.
    -   Use FastAPI for the web framework.
    -   Structure the project into a logical `app` module with sub-modules for `api`, `core`, `models`, `services`, etc.
    -   Set up `pyproject.toml` for dependency management.

-   **Task 1.2: Database & Migrations**
    -   Integrate SQLAlchemy for the ORM.
    -   Set up Alembic for handling database migrations.
    -   Create the initial migration for the `users` table. The `User` model should include `id`, `tg_id`, `username`, and `lang`.

-   **Task 1.3: Core Configuration & Health Check**
    -   Implement a `core/config.py` module using Pydantic to manage all environment variables (`DATABASE_URL`, `BOT_TOKEN`, etc.).
    -   Create a `.env.example` file with all required variables.
    -   Add a `/health` endpoint to the API to verify that the service is running.

---

## 4. Phase 2: Core Bot & i18n

**Goal:** Implement a functional Telegram bot with a proper, working internationalization (i18n) system.

-   **Task 2.1: Bot Initialization**
    -   Integrate the `python-telegram-bot` library.
    -   Create a `bot/main.py` module responsible for initializing the bot, setting commands, and registering handlers.
    -   The bot should be started in the background from the FastAPI `lifespan` manager.

-   **Task 2.2: Internationalization (i18n) Setup**
    -   Implement the translation system using `pybabel` and `gettext`.
    -   Create the directory structure `app/i18n/<lang>/LC_MESSAGES/`.
    -   Generate the `.pot` template file and create `.po` files for at least English (`en`) and Italian (`it`).
    -   **Crucially, add a script or command to compile `.po` files to `.mo` files and document this in the `README.md`.**
    -   The translator function must use absolute paths to the `localedir` to avoid runtime errors.

-   **Task 2.3: Basic Command Handlers**
    -   Implement the `/start` and `/lang` commands.
    -   The `/start` command should greet the user and show the main menu with inline buttons.
    -   The `/lang` command should allow users to change their language preference, which must be saved to the `users` table in the database.
    -   All text displayed by the bot **must** use the i18n system.

---

## 5. Phase 3: Feature Implementation

**Goal:** Re-implement the core business logic of the bot.

-   **Task 3.1: Gig Creation Flow**
    -   Implement the "New Gig" feature for both USDT and BTC using a `ConversationHandler`.
    -   The flow should ask for Title, Price, and Description.
    -   The new gig must be saved to the database.

-   **Task 3.2: Listings & Purchase Flow**
    -   Implement the `/listings` command to show active gigs.
    -   Implement the `/buy <gig_id>` command, also as a `ConversationHandler`.
    -   This flow must create an `Order` in the database and provide the user with a deposit address.

-   **Task 3.3: Order & Escrow Management**
    -   Implement the `/orders` and `/mygigs` commands to show user-specific information.
    -   Implement the `/confirm_tx`, `/release`, and `/dispute` commands. These are critical and must correctly handle the order status changes in the database.

---

## 6. Phase 4: Admin Dashboard

**Goal:** Rebuild the secure admin panel for dispute resolution.

-   **Task 4.1: Admin API**
    -   Create a new `api/admin.py` module.
    -   Implement secure login for the admin user (ID should be configured via environment variable).
    -   Create endpoints to:
        -   List open disputes.
        -   View dispute details.
        -   Resolve disputes (release funds to buyer or seller).

-   **Task 4.2: Admin Frontend**
    -   Create the HTML templates (`login.html`, `dashboard.html`, `dispute_detail.html`) using Jinja2.
    -   The frontend should be simple, clean, and functional. Use a lightweight CSS framework if needed, or write minimal custom CSS.
    -   The frontend will interact with the Admin API.

---

This plan provides a clear path forward. Please start with Phase 1 and submit a Pull Request upon completion. Let's bring this project back to its full potential.
