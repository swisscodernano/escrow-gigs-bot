from sqlalchemy.orm import Session

from app.models.user import User


def get_or_create_user(db: Session, tg_id: str, username: str | None = None) -> User:
    """
    Retrieves a user by their Telegram ID or creates a new one if they don't exist.
    """
    user = db.query(User).filter(User.tg_id == tg_id).first()
    if not user:
        user = User(tg_id=tg_id, username=username)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def update_user_lang(db: Session, user_id: int, lang: str) -> None:
    """
    Updates the language preference for a given user.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.lang = lang
        db.commit()
