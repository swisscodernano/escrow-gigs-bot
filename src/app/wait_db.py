import os, time
import psycopg2

host = os.getenv("POSTGRES_HOST", "db")
port = int(os.getenv("POSTGRES_PORT", "5432"))
db   = os.getenv("POSTGRES_DB", "escrowdb")
usr  = os.getenv("POSTGRES_USER", "escrow")
pwd  = os.getenv("POSTGRES_PASSWORD", "escrowpass")

for i in range(120):
    try:
        conn = psycopg2.connect(host=host, port=port, dbname=db, user=usr, password=pwd)
        conn.close()
        print("[wait_db] DB ready")
        break
    except Exception:
        print(f"[wait_db] waiting... ({i+1}/120)")
        time.sleep(1)
else:
    raise SystemExit("DB not ready after 120s")
