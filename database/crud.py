from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import AsyncSessionLocal
from database.models import Trip, User, RefreshToken
from auth.security import hash_password


async def create_user(db: AsyncSession, email: str, password: str, full_name: str | None = None) -> User:
    hashed = hash_password(password)
    user = User(
        email=email,
        hashed_password=hashed,
        full_name=full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def update_user(db: AsyncSession, user_id: UUID, **fields) -> User:
    await db.execute(update(User).where(User.id == user_id).values(**fields))
    await db.commit()
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one()


async def create_trip(
    db: AsyncSession,
    user_id: UUID,
    request_text: str,
    origin: str,
    destination: str,
    event_date: str,
    venue: str,
    travelers: int = 1,
    thread_id: str | None = None,
) -> Trip:
    trip = Trip(
        user_id=user_id,
        request_text=request_text,
        origin=origin,
        destination=destination,
        event_date=event_date,
        venue=venue,
        travelers=travelers,
        thread_id=thread_id,
        status="in_progress",
    )
    db.add(trip)
    await db.commit()
    await db.refresh(trip)
    return trip


async def update_trip_status(
    db: AsyncSession,
    trip_id: UUID,
    status: str,
    final_state: dict | None = None,
) -> Trip:
    values = {"status": status}
    if status in ("completed", "failed"):
        values["completed_at"] = datetime.now(timezone.utc)
    if final_state:
        values["final_report"] = final_state.get("final_report")
        values["flight_details"] = final_state.get("flight_details")
        values["hotel_details"] = final_state.get("hotel_details")
        values["weather_details"] = final_state.get("weather_details")
        values["errors"] = final_state.get("errors")
    await db.execute(update(Trip).where(Trip.id == trip_id).values(**values))
    await db.commit()
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    return result.scalar_one()


async def get_user_trips(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 20,
    offset: int = 0,
) -> list[Trip]:
    result = await db.execute(
        select(Trip)
        .where(Trip.user_id == user_id)
        .order_by(Trip.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_trip_by_id(db: AsyncSession, trip_id: UUID, user_id: UUID | None = None) -> Trip | None:
    query = select(Trip).where(Trip.id == trip_id)
    if user_id is not None:
        query = query.where(Trip.user_id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_trip_by_thread_id(db: AsyncSession, thread_id: str) -> Trip | None:
    result = await db.execute(select(Trip).where(Trip.thread_id == thread_id))
    return result.scalar_one_or_none()


async def create_refresh_token(
    db: AsyncSession,
    user_id: UUID,
    token_hash: str,
    expires_at: datetime,
    device_name: str | None = None,
    ip_address: str | None = None,
) -> RefreshToken:
    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        device_name=device_name,
        ip_address=ip_address,
    )
    db.add(refresh_token)
    await db.commit()
    await db.refresh(refresh_token)
    return refresh_token


async def get_refresh_token_by_hash(db: AsyncSession, token_hash: str) -> RefreshToken | None:
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    return result.scalar_one_or_none()


async def revoke_refresh_token(db: AsyncSession, token_id: UUID) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.id == token_id)
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()
