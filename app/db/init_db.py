from app.db_core import Base, engine
from app.models import Dispute, Feedback, Gig, Order, User  # noqa: F401


def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created.")


if __name__ == "__main__":
    init_db()
