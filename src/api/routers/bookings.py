"""Bookings API router.

This module provides endpoints for managing bookings in the system.
"""

from datetime import datetime, time, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.models.database import Booking, Customer, Service
from src.api.models.schemas import (
    AvailabilityQuery,
    BookingCreate,
    BookingResponse,
    BookingUpdate,
)
from src.core.database import get_db

router = APIRouter()


@router.get("/", response_model=list[BookingResponse])
async def get_bookings(
    skip: int = 0,
    limit: int = 100,
    customer_id: str | None = Query(None, description="Filter by customer ID (UUID)"),
    service_id: str | None = Query(None, description="Filter by service ID (UUID)"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get all bookings with optional filters.

    Args:
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        customer_id: Optional customer ID filter (UUID).
        service_id: Optional service ID filter (UUID).
        status_filter: Optional status filter.
        db: Database session.

    Returns:
        List of bookings with customer and service details.
    """
    query = select(Booking).options(
        selectinload(Booking.customer),
        selectinload(Booking.service),
        selectinload(Booking.barber),
    )

    if customer_id:
        query = query.where(Booking.customer_id == customer_id)
    if service_id:
        query = query.where(Booking.service_id == service_id)
    if status_filter:
        query = query.where(Booking.status == status_filter)

    query = query.offset(skip).limit(limit).order_by(Booking.start_time.desc())

    result = await db.execute(query)
    bookings = result.scalars().all()

    return bookings


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get a specific booking by ID.

    Args:
        booking_id: Booking ID (UUID).
        db: Database session.

    Returns:
        Booking record with customer and service details.

    Raises:
        HTTPException: If booking not found.
    """
    result = await db.execute(
        select(Booking)
        .options(
            selectinload(Booking.customer),
            selectinload(Booking.service),
            selectinload(Booking.barber),
        )
        .where(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with id {booking_id} not found",
        )

    return booking


@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking_in: BookingCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new booking.

    Args:
        booking_in: Booking data.
        db: Database session.

    Returns:
        Created booking record.

    Raises:
        HTTPException: If customer or service not found, or time slot unavailable.
    """
    # Verify customer exists
    customer_result = await db.execute(
        select(Customer).where(Customer.id == booking_in.customer_id)
    )
    if not customer_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with id {booking_in.customer_id} not found",
        )

    # Verify service exists
    service_result = await db.execute(select(Service).where(Service.id == booking_in.service_id))
    service = service_result.scalar_one_or_none()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service with id {booking_in.service_id} not found",
        )

    # Calculate end time
    end_time = booking_in.start_time + timedelta(minutes=service.duration_minutes)

    # Check for conflicts (simplified - would need more complex logic in production)
    conflict_query = select(Booking).where(
        Booking.customer_id == booking_in.customer_id,
        Booking.status == "confirmed",
        Booking.start_time < end_time,
        Booking.end_time > booking_in.start_time,
    )
    conflict_result = await db.execute(conflict_query)
    if conflict_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Time slot conflicts with existing booking",
        )

    # Create booking
    booking_data = booking_in.model_dump()
    booking_data["end_time"] = end_time
    booking_data["status"] = "confirmed"

    booking = Booking(**booking_data)
    db.add(booking)
    await db.commit()

    # Reload with relationships using selectinload
    result = await db.execute(
        select(Booking)
        .where(Booking.id == booking.id)
        .options(
            selectinload(Booking.customer),
            selectinload(Booking.service),
            selectinload(Booking.barber),
        )
    )
    booking = result.scalar_one()

    return booking


@router.put("/{booking_id}", response_model=BookingResponse)
async def update_booking(
    booking_id: str,
    booking_in: BookingUpdate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update an existing booking.

    Args:
        booking_id: Booking ID (UUID).
        booking_in: Updated booking data (partial).
        db: Database session.

    Returns:
        Updated booking record.

    Raises:
        HTTPException: If booking not found.
    """
    result = await db.execute(
        select(Booking)
        .options(
            selectinload(Booking.customer),
            selectinload(Booking.service),
            selectinload(Booking.barber),
        )
        .where(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with id {booking_id} not found",
        )

    # Update only provided fields
    update_data = booking_in.model_dump(exclude_unset=True)

    # If start_time is updated, recalculate end_time
    if "start_time" in update_data:
        service_result = await db.execute(select(Service).where(Service.id == booking.service_id))
        service = service_result.scalar_one()
        update_data["end_time"] = update_data["start_time"] + timedelta(
            minutes=service.duration_minutes
        )

    for field, value in update_data.items():
        setattr(booking, field, value)

    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(Booking)
        .where(Booking.id == booking.id)
        .options(
            selectinload(Booking.customer),
            selectinload(Booking.service),
            selectinload(Booking.barber),
        )
    )
    booking = result.scalar_one()

    return booking


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_booking(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Cancel a booking (soft delete by setting status to 'cancelled').

    Args:
        booking_id: Booking ID (UUID).
        db: Database session.

    Raises:
        HTTPException: If booking not found.
    """
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with id {booking_id} not found",
        )

    booking.status = "cancelled"
    await db.commit()


@router.post("/availability/")
async def check_availability(
    query: AvailabilityQuery,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Check available time slots for a service on a specific date.

    Args:
        query: Availability query with date, service_id, and optional preferred_stylist.
        db: Database session.

    Returns:
        List of available time slots with start_time, end_time, and availability status.

    Raises:
        HTTPException: If service not found.
    """
    # Verify service exists
    service_result = await db.execute(select(Service).where(Service.id == query.service_id))
    service = service_result.scalar_one_or_none()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service with id {query.service_id} not found",
        )

    # Parse the date string
    try:
        check_date = datetime.strptime(query.date, "%Y-%m-%d").date()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format. Use YYYY-MM-DD: {e}",
        ) from e

    # Generate time slots (9 AM to 6 PM, every 30 minutes)
    slots = []
    current_time = time(9, 0)
    end_time = time(18, 0)

    while current_time < end_time:
        slot_start = datetime.combine(check_date, current_time)
        slot_end = slot_start + timedelta(minutes=service.duration_minutes)

        # Check if slot is available (no conflicting bookings)
        conflict_query = select(Booking).where(
            Booking.status == "confirmed",
            Booking.start_time < slot_end,
            Booking.end_time > slot_start,
        )

        # If preferred stylist specified, filter by barber name (requires join)
        if query.preferred_stylist:
            from src.api.models.database import Barber

            conflict_query = conflict_query.join(Barber, Booking.barber_id == Barber.id).where(
                Barber.name == query.preferred_stylist
            )

        conflict_result = await db.execute(conflict_query)
        has_conflict = conflict_result.scalar_one_or_none() is not None

        slots.append(
            {
                "start_time": slot_start.strftime("%H:%M"),
                "end_time": slot_end.strftime("%H:%M"),
                "available": not has_conflict,
            }
        )

        # Move to next slot (30-minute intervals)
        hours = current_time.hour
        minutes = current_time.minute + 30
        if minutes >= 60:
            hours += 1
            minutes -= 60
        current_time = time(hours, minutes)

    return slots
