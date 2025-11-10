"""Services API router.

This module provides endpoints for managing services in the system.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.database import Service
from src.api.models.schemas import ServiceCreate, ServiceResponse, ServiceUpdate
from src.core.database import get_db

router = APIRouter()


@router.get("/", response_model=list[ServiceResponse])
async def get_services(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get all services.

    Args:
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        db: Database session.

    Returns:
        List of services.
    """
    result = await db.execute(select(Service).offset(skip).limit(limit))
    services = result.scalars().all()
    return services


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get a specific service by ID.

    Args:
        service_id: Service ID (UUID).
        db: Database session.

    Returns:
        Service record.

    Raises:
        HTTPException: If service not found.
    """
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service with id {service_id} not found",
        )

    return service


@router.post("/", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    service_in: ServiceCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new service.

    Args:
        service_in: Service data.
        db: Database session.

    Returns:
        Created service record.
    """
    service = Service(**service_in.model_dump())
    db.add(service)
    await db.commit()
    await db.refresh(service)

    return service


@router.put("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: str,
    service_in: ServiceUpdate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update an existing service.

    Args:
        service_id: Service ID (UUID).
        service_in: Updated service data (partial).
        db: Database session.

    Returns:
        Updated service record.

    Raises:
        HTTPException: If service not found.
    """
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service with id {service_id} not found",
        )

    # Update only provided fields
    update_data = service_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service, field, value)

    await db.commit()
    await db.refresh(service)

    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a service (soft delete by marking inactive).

    Args:
        service_id: Service ID (UUID).
        db: Database session.

    Raises:
        HTTPException: If service not found.
    """
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service with id {service_id} not found",
        )

    service.is_active = False
    await db.commit()
