from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.user import User
from app.services.user_service import get_or_create_user, update_user_lang

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Fixture to create a new database and session for each test function
@pytest.fixture(scope="function")
def db_session() -> Iterator[Session]:
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_get_or_create_user(db_session: Session):
    # Test creating a new user
    user = get_or_create_user(db_session, "12345", "testuser")
    assert user.tg_id == "12345"
    assert user.username == "testuser"
    assert user.lang == "en"

    # Verify it's in the database
    retrieved_user = db_session.query(User).filter(User.tg_id == "12345").first()
    assert retrieved_user is not None
    assert retrieved_user.id == user.id

    # Test retrieving the same user
    user2 = get_or_create_user(
        db_session, "12345", "testuser_updated_name_should_not_update"
    )
    assert user2.id == user.id
    assert user2.username == "testuser"  # Username should not be updated

    # Test creating another user
    user3 = get_or_create_user(db_session, "54321", "anotheruser")
    assert user3.tg_id == "54321"
    assert user3.id != user.id


def test_update_user_lang(db_session: Session):
    # Create a user first
    user = User(tg_id="98765", username="languser")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Update the user's language
    update_user_lang(db_session, user.id, "it")

    # Verify the language was updated
    updated_user = db_session.query(User).filter(User.id == user.id).first()
    assert updated_user is not None
    assert updated_user.lang == "it"
