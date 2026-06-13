import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.models.user import Base


class IntegrationConnection(Base):
    __tablename__ = "integration_connections"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    first_connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_disconnect_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
