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

## 3. Phase 1: Foundation & API Setup (COMPLETE)

**Goal:** Establish a robust project structure with a functional FastAPI backend and database connectivity.

---

## 4. Phase 2: Parallel Development

**Goal:** Accelerate development by working on the Bot Interface and Data Models simultaneously. Jules, you can create two separate branches and work on these tasks at the same time.

-   **Track A: Core Bot & i18n**
    -   **Description:** Build the user-facing bot, commands, and translation system.
    -   **Task File:** See `JULES_TASKS/PHASE_2A_CORE_BOT.md`
    -   **Branch:** `feature/phase-2a-core-bot`

-   **Track B: Data Models & Migrations**
    -   **Description:** Define all database tables using SQLAlchemy models and create Alembic migrations.
    -   **Task File:** See `JULES_TASKS/PHASE_2B_DATA_MODELS.md`
    -   **Branch:** `feature/phase-2b-data-models`

---

## 5. Phase 3: Feature Implementation

**Goal:** Re-implement the core business logic of the bot. This phase will begin after both tasks in Phase 2 are complete and merged.

-   **Task 3.1: Gig Creation Flow**
-   **Task 3.2: Listings & Purchase Flow**
-   **Task 3.3: Order & Escrow Management**

---

## 6. Phase 4: Admin Dashboard

**Goal:** Rebuild the secure admin panel for dispute resolution. This can be parallelized with Phase 3.

-   **Task 4.1: Admin API**
-   **Task 4.2: Admin Frontend**

---

This plan provides a clear path forward. Please start with the parallel tasks in Phase 2. Let's bring this project back to its full potential.
