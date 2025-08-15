
import os
import time
import psycopg2

DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_NAME = os.getenv("POSTGRES_DB", "gigs")
DB_USER = os.getenv("POSTGRES_USER", "gigs")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "gigs")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

if __name__ == "__main__":
    print("Waiting for database...")
    while True:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                port=DB_PORT
            )
            conn.close()
            print("Database is ready!")
            break
        except psycopg2.OperationalError as e:
            print(f"Database not ready yet: {e}")
            time.sleep(1)
