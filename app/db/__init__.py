"""Compatibility shim for legacy imports like 'from app.db import SessionLocal'."""
from app.db_core import Base, engine, SessionLocal, get_db

__all__ = ("Base", "engine", "SessionLocal", "get_db")
