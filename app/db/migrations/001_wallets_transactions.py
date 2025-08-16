"""Create wallets and transactions tables"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
)
from sqlalchemy.sql import func

metadata = MetaData()

Wallets = Table(
    "wallets",
    metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("balance", Numeric(18, 2), default=0),
    Column("currency", String(8), default="USD"),
)

Transactions = Table(
    "transactions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id"), index=True),
    Column("type", String(16)),
    Column("amount", Numeric(18, 2)),
    Column("status", String(16), default="pending"),
    Column("ext_ref", String(64), default=""),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)
