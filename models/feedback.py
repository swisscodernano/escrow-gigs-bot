
from sqlalchemy import Integer, String, Numeric, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from db import Base

class Feedback(Base):
    __tablename__ = "feedbacks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), index=True, unique=True) # One feedback per order
    reviewer_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    reviewee_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    score: Mapped[int] = mapped_column(Integer) # Score from 1 to 5
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order = relationship("Order")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    reviewee = relationship("User", foreign_keys=[reviewee_id])
