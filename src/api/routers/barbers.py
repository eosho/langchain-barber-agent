"""Barbers API router.

This module provides endpoints for managing barbers in the system.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.database import Barber
from src.api.models.schemas import BarberCreate, BarberResponse, BarberUpdate
from src.core.database import get_db

router = APIRouter()


@router.get("/", response_model=list[BarberResponse])
async def get_barbers(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get all barbers.

    Args:
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        db: Database session.

    Returns:
        List of barbers.
    """
    result = await db.execute(select(Barber).offset(skip).limit(limit))
    barbers = result.scalars().all()
    return barbers


@router.get("/{barber_id}", response_model=BarberResponse)
async def get_barber(
    barber_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get a specific barber by ID.

    Args:
        barber_id: Barber ID (UUID).
        db: Database session.

    Returns:
        Barber record.

    Raises:
        HTTPException: If barber not found.
    """
    result = await db.execute(select(Barber).where(Barber.id == barber_id))
    barber = result.scalar_one_or_none()

    if not barber:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Barber with id {barber_id} not found",
        )

    return barber


@router.post("/", response_model=BarberResponse, status_code=status.HTTP_201_CREATED)
async def create_barber(
    barber_in: BarberCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new barber.

    Args:
        barber_in: Barber data.
        db: Database session.

    Returns:
        Created barber record.

    Raises:
        HTTPException: If email already exists.
    """
    # Check for duplicate email
    result = await db.execute(select(Barber).where(Barber.email == barber_in.email))
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Barber with email {barber_in.email} already exists",
        )

    barber = Barber(**barber_in.model_dump())
    db.add(barber)
    await db.commit()
    await db.refresh(barber)

    return barber


@router.put("/{barber_id}", response_model=BarberResponse)
async def update_barber(
    barber_id: str,
    barber_in: BarberUpdate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update an existing barber.

    Args:
        barber_id: Barber ID (UUID).
        barber_in: Updated barber data (partial).
        db: Database session.

    Returns:
        Updated barber record.

    Raises:
        HTTPException: If barber not found.
    """
    result = await db.execute(select(Barber).where(Barber.id == barber_id))
    barber = result.scalar_one_or_none()

    if not barber:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Barber with id {barber_id} not found",
        )

    # Update only provided fields
    update_data = barber_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(barber, field, value)

    await db.commit()
    await db.refresh(barber)

    return barber


@router.delete("/{barber_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_barber(
    barber_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a barber (soft delete by marking inactive).

    Args:
        barber_id: Barber ID (UUID).
        db: Database session.

    Raises:
        HTTPException: If barber not found.
    """
    result = await db.execute(select(Barber).where(Barber.id == barber_id))
    barber = result.scalar_one_or_none()

    if not barber:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Barber with id {barber_id} not found",
        )

    barber.is_active = False
    await db.commit()
