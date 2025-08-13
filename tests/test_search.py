import os, sys, pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app.services.search import search_gigs
from app.bot.handlers import search as handler

@pytest.fixture
def sessionmaker_():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE gigs (id INTEGER PRIMARY KEY, title TEXT, description TEXT, price_usd REAL, active INTEGER)"))
        conn.execute(text("CREATE VIRTUAL TABLE gigs_fts USING fts5(title, description, content='gigs', content_rowid='id')"))
        gigs = [
            (1, "Red apple", "Fresh red apples", 10.0, 1),
            (2, "Green apple", "Sour green apple", 12.0, 1),
            (3, "Banana", "Yellow banana", 5.0, 1),
        ]
        for g in gigs:
            conn.execute(text("INSERT INTO gigs VALUES (:id,:t,:d,:p,:a)"),
                         {"id": g[0], "t": g[1], "d": g[2], "p": g[3], "a": g[4]})
            conn.execute(text("INSERT INTO gigs_fts(rowid,title,description) VALUES (:id,:t,:d)"),
                         {"id": g[0], "t": g[1], "d": g[2]})
    return sessionmaker(bind=engine)

def test_search_ranking(sessionmaker_):
    db: Session = sessionmaker_()
    res = search_gigs(db, "red apple")
    db.close()
    assert [r["id"] for r in res][:2] == [1, 2]

class _Msg:
    def __init__(self):
        self.sent = []
    async def reply_text(self, text, **kwargs):
        self.sent.append(text)

class _Update:
    def __init__(self):
        self.effective_message = _Msg()
        self.message = self.effective_message

class _Ctx:
    def __init__(self, args=None):
        self.args = args or []

def test_cmd_search_happy_path(sessionmaker_, monkeypatch):
    monkeypatch.setattr(handler, "SessionLocal", sessionmaker_)
    u = _Update(); c = _Ctx(["apple"])
    import asyncio
    asyncio.run(handler.cmd_search(u, c))
    assert any("Red apple" in m for m in u.effective_message.sent)
