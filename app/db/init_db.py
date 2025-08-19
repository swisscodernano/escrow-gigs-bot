
from app.db_core import Base, engine
from app.models import User, Gig, Order, Dispute, Feedback # Import models to ensure they are registered with Base.metadata

def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created.")

if __name__ == "__main__":
    init_db()
