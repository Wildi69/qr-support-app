from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Enum,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.database import Base


# --- Enums --------------------------------------------------------------------

class TicketStatus(str, PyEnum):
    new = "new"
    open = "open"
    closed = "closed"


class EmailStatus(str, PyEnum):
    queued = "queued"
    sent = "sent"
    failed = "failed"


# --- Models -------------------------------------------------------------------

class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    serial: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    qr_tokens: Mapped[list["QRToken"]] = relationship("QRToken", back_populates="machine", cascade="all, delete-orphan")
    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="machine", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Machine serial={self.serial!r} type={self.type!r}>"


class QRToken(Base):
    __tablename__ = "qr_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    # Optional expiry; if null, token does not expire
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    machine: Mapped["Machine"] = relationship("Machine", back_populates="qr_tokens")

    def __repr__(self) -> str:
        return f"<QRToken token={self.token!r} machine_id={self.machine_id}>"


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        # Keep summaries short for UI/export; enforced again at API level
        UniqueConstraint("id", name="uq_tickets_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    machine_id: Mapped[Optional[int]] = mapped_column(ForeignKey("machines.id", ondelete="SET NULL"), nullable=True, index=True)

    operator_name: Mapped[str] = mapped_column(String(120), nullable=False)
    operator_phone: Mapped[str] = mapped_column(String(40), nullable=False)
    summary: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[TicketStatus] = mapped_column(Enum(TicketStatus), default=TicketStatus.new, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    machine: Mapped[Optional["Machine"]] = relationship("Machine", back_populates="tickets")
    emails: Mapped[list["EmailLog"]] = relationship("EmailLog", back_populates="ticket", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Ticket id={self.id} status={self.status}>"


class EmailLog(Base):
    __tablename__ = "email_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)

    to_addr: Mapped[str] = mapped_column(String(254), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[EmailStatus] = mapped_column(Enum(EmailStatus), default=EmailStatus.queued, nullable=False)

    # Observability fields (added by migration 40337e53cf25)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="emails")

    def __repr__(self) -> str:
        return f"<EmailLog id={self.id} ticket_id={self.ticket_id} status={self.status}>"


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)   # e.g., 'public:operator', 'admin:username'
    action: Mapped[str] = mapped_column(String(120), nullable=False)  # e.g., 'ticket.create', 'machine.update'
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)  # 'ticket', 'machine', etc.
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # extra context
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<AuditEvent action={self.action!r} entity={self.entity_type}:{self.entity_id}>"
