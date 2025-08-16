from sqlalchemy import create_engine, inspect, text

from app.config import settings


def run_migration():
    DATABASE_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    engine = create_engine(DATABASE_URL)

    # Check if the column exists before attempting to add it
    inspector = inspect(engine)
    columns = inspector.get_columns("users")
    column_names = [col["name"] for col in columns]

    if "btc_address" not in column_names:
        with engine.connect() as connection:
            connection.execute(
                text(
                    "ALTER TABLE users ADD COLUMN btc_address VARCHAR(128) DEFAULT '';"
                )
            )
            connection.commit()
        print("Migration: Added btc_address column to users table.")
    else:
        print("Migration: btc_address column already exists in users table.")


if __name__ == "__main__":
    run_migration()
