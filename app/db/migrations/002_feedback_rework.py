from sqlalchemy import inspect, text

from app.db_core import engine


def run_migration():
    """
    This migration script reworks the 'feedbacks' table:
    1. Adds a 'review_type' column.
    2. Removes the old unique constraint on 'order_id'.
    3. Adds a new composite unique constraint on ('order_id', 'reviewer_id').
    """
    inspector = inspect(engine)

    print("Running migration for 'feedbacks' table...")

    # --- 1. Add 'review_type' column if it doesn't exist ---
    columns = inspector.get_columns("feedbacks")
    column_names = [col["name"] for col in columns]
    if "review_type" not in column_names:
        with engine.connect() as connection:
            connection.execute(
                text(
                    "ALTER TABLE feedbacks ADD COLUMN review_type VARCHAR(16) DEFAULT 'buyer_review' NOT NULL;"
                )
            )
            connection.commit()
            print("Migration: Added 'review_type' column to 'feedbacks' table.")
    else:
        print("Migration: 'review_type' column already exists in 'feedbacks' table.")

    # --- 2. Find and drop the old single-column unique constraint on 'order_id' ---
    unique_constraints = inspector.get_unique_constraints("feedbacks")
    old_constraint_name = None
    for const in unique_constraints:
        # The constraint could have been created on a single column list
        if const["column_names"] == ["order_id"]:
            old_constraint_name = const["name"]
            break

    if old_constraint_name:
        with engine.connect() as connection:
            connection.execute(
                text(f'ALTER TABLE feedbacks DROP CONSTRAINT "{old_constraint_name}";')
            )
            connection.commit()
            print(
                f"Migration: Dropped old unique constraint '{old_constraint_name}' on order_id."
            )
    else:
        print(
            "Migration: No single-column unique constraint found on 'order_id' to drop."
        )

    # --- 3. Add the new composite unique constraint if it doesn't exist ---
    # Re-inspect to get the current state of constraints
    inspector = inspect(engine)
    constraints = inspector.get_unique_constraints("feedbacks")
    constraint_names = [c["name"] for c in constraints]

    if "_order_reviewer_uc" not in constraint_names:
        with engine.connect() as connection:
            connection.execute(
                text(
                    "ALTER TABLE feedbacks ADD CONSTRAINT _order_reviewer_uc UNIQUE (order_id, reviewer_id);"
                )
            )
            connection.commit()
            print(
                "Migration: Added composite unique constraint '_order_reviewer_uc' on (order_id, reviewer_id)."
            )
    else:
        print(
            "Migration: Composite unique constraint '_order_reviewer_uc' on (order_id, reviewer_id) already exists."
        )

    print("Migration for 'feedbacks' table finished.")


if __name__ == "__main__":
    run_migration()
