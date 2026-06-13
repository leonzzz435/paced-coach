import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.models.user import Base


class CoachProposal(Base):
    __tablename__ = "coach_proposals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    thread_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coach_threads.id"),
        nullable=True,
        index=True,
    )
    source_event_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)

    weekly_plan_version: Mapped[int] = mapped_column(Integer, nullable=False)
    assistant_message: Mapped[str] = mapped_column(String(), nullable=False)
    ops: Mapped[dict] = mapped_column(JSONB, nullable=False)
    origin: Mapped[str] = mapped_column(String(40), nullable=False, default="coach_chat")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    rejection_reason: Mapped[str | None] = mapped_column(String(), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
