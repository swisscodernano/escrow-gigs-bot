from functools import wraps
from app.db import SessionLocal

def db_session_decorator(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        db = SessionLocal()
        try:
            # Pass the database session as a keyword argument to the decorated function
            kwargs['db'] = db
            result = await func(*args, **kwargs)
            db.commit()
            return result
        except Exception as e:
            db.rollback()
            # Optionally, re-raise the exception after rolling back
            raise e
        finally:
            db.close()
    return wrapper
