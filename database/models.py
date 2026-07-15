import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("uuid_generate_v4()"))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    updated_at = Column(DateTime(timezone=True), onupdate=text("NOW()"))
    oauth_provider = Column(String, nullable=True)
    oauth_id = Column(String, nullable=True)

    trips = relationship("Trip", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("uuid_generate_v4()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True, index=True)
    device_name = Column(Text, nullable=True)
    ip_address = Column(Text, nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="refresh_tokens")


class Trip(Base):
    __tablename__ = "trips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("uuid_generate_v4()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    request_text = Column(Text)
    origin = Column(String)
    destination = Column(String)
    event_date = Column(String)
    venue = Column(String)
    travelers = Column(Integer, default=1)
    status = Column(String, default="in_progress")
    final_report = Column(Text, nullable=True)
    flight_details = Column(JSON, nullable=True)
    hotel_details = Column(JSON, nullable=True)
    weather_details = Column(JSON, nullable=True)
    errors = Column(JSON, nullable=True)
    thread_id = Column(String, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="trips")
