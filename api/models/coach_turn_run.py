import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.models.user import Base


class CoachTurnRun(Base):
    __tablename__ = "coach_turn_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coach_threads.id"),
        nullable=False,
        index=True,
    )
    turn_seq_anchor: Mapped[int] = mapped_column(Integer, nullable=False)
    user_message_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coach_events.id"),
        nullable=False,
    )
    response_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coach_events.id"),
        nullable=True,
    )
    langsmith_project: Mapped[str | None] = mapped_column(String(200), nullable=True)
    langsmith_trace_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    langsmith_root_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    run_name: Mapped[str] = mapped_column(String(80), nullable=False, default="continuum_coach_turn")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_message_event_id", name="uq_coach_turn_runs_user_message_event_id"),
    )
