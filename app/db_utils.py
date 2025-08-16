from functools import wraps

from app.db import SessionLocal


def db_session_decorator(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        db = SessionLocal()
        try:
            kwargs["db"] = db
            result = await func(*args, **kwargs)
            db.commit()
            return result
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    return wrapper
