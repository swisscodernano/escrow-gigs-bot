# Task: Phase 2B - Data Models & Migrations

Hi Jules,

This task runs in parallel with the Core Bot setup. Your focus here will be on defining the data structure that will power the entire application.

**The Goal:** Build a complete and robust data model for the application.

**The Task: Define All SQLAlchemy Models and Create Alembic Migrations**

You will create the Python classes for all database tables and generate the corresponding Alembic migration scripts to build the schema.

**Key Requirements & Features to Implement:**

1.  **SQLAlchemy Models:**
    *   In the `app/models/` directory, create the following SQLAlchemy models with the specified fields:
        *   **`Gig`**: `id`, `seller_id` (FK to User), `title`, `description`, `price_usd` (Numeric), `currency` (String), `active` (Boolean, default `True`).
        *   **`Order`**: `id`, `gig_id` (FK to Gig), `buyer_id` (FK to User), `seller_id` (FK to User), `status` (String, e.g., 'AWAIT_DEPOSIT', 'FUNDS_HELD', 'RELEASED', 'DISPUTED'), `expected_amount` (Numeric), `escrow_fee_pct` (Numeric), `deposit_address` (String), `txid` (String, nullable).
        *   **`Dispute`**: `id`, `order_id` (FK to Order), `opened_by` (FK to User), `reason` (Text), `status` (String, e.g., 'OPEN', 'RESOLVED').

2.  **Database Migrations:**
    *   For each model you create, generate a new Alembic migration script.
    *   Ensure all relationships (Foreign Keys) are correctly defined with back-references where appropriate.
    *   Review the generated migration scripts to ensure they accurately reflect the model definitions.

**Workflow:**

1.  **Branching:** Create your feature branch from the latest `new-main`.
    *   `git checkout new-main && git pull`
    *   `git checkout -b feature/phase-2b-data-models`
2.  **Code Quality & Testing:** Run `black`, `isort`, `flake8`, and `mypy` before committing.
3.  **Submission:** When you have created all models and migrations, push your `feature/phase-2b-data-models` branch to GitHub and open a Pull Request to `new-main`.

- Gemini
