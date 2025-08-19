"""Compatibility shim for legacy imports like 'from db import SessionLocal'."""
from ..db_core import Base, engine, SessionLocal, get_db

__all__ = ("Base", "engine", "SessionLocal", "get_db")
