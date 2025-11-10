"""Customers router for managing customer records.

This module provides REST API endpoints for CRUD operations on customers.

Example:
    >>> import httpx
    >>> response = httpx.get("http://localhost:8000/api/v1/customers")
    >>> customers = response.json()
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.database import Customer
from src.api.models.schemas import CustomerCreate, CustomerResponse, CustomerUpdate
from src.core.database import get_db

router = APIRouter()


@router.get("/", response_model=list[CustomerResponse])
async def list_customers(
    skip: int = 0,
    limit: int = 100,
    email: str | None = None,
    phone: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List all customers with optional filtering.

    Args:
        skip: Number of records to skip (pagination).
        limit: Maximum number of records to return.
        email: Filter by email (partial match).
        phone: Filter by phone number (partial match).
        db: Database session.

    Returns:
        List of customer records.

    Example:
        >>> GET /api/v1/customers?email=john@example.com
    """
    query = select(Customer)

    if email:
        query = query.where(Customer.email.ilike(f"%{email}%"))

    if phone:
        query = query.where(Customer.phone.ilike(f"%{phone}%"))

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    customers = result.scalars().all()

    return customers


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get a specific customer by ID.

    Args:
        customer_id: Customer ID.
        db: Database session.

    Returns:
        Customer record.

    Raises:
        HTTPException: If customer not found.

    Example:
        >>> GET /api/v1/customers/1
    """
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with id {customer_id} not found",
        )

    return customer


@router.get("/lookup/by-contact", response_model=CustomerResponse | None)
async def lookup_customer_by_contact(
    email: str | None = Query(None),
    phone: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Lookup customer by email or phone (exact match).

    Args:
        email: Customer email.
        phone: Customer phone number.
        db: Database session.

    Returns:
        Customer record if found, else None.

    Example:
        >>> GET /api/v1/customers/lookup/by-contact?email=john@example.com
    """
    if not email and not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Must provide either email or phone"
        )

    query = select(Customer)

    if email:
        query = query.where(Customer.email == email)
    elif phone:
        query = query.where(Customer.phone == phone)

    result = await db.execute(query)
    customer = result.scalar_one_or_none()

    return customer


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_in: CustomerCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new customer.

    Args:
        customer_in: Customer data.
        db: Database session.

    Returns:
        Created customer record.

    Raises:
        HTTPException: If customer with email/phone already exists.

    Example:
        >>> POST /api/v1/customers
        >>> {
        ...   "name": "John Doe",
        ...   "email": "john@example.com",
        ...   "phone": "+1234567890"
        ... }
    """
    # Check for existing customer
    existing = await db.execute(
        select(Customer).where(
            (Customer.email == customer_in.email) | (Customer.phone == customer_in.phone)
        )
    )

    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer with this email or phone already exists",
        )

    customer = Customer(**customer_in.model_dump())
    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    customer_in: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update an existing customer.

    Args:
        customer_id: Customer ID (UUID).
        customer_in: Updated customer data (partial).
        db: Database session.

    Returns:
        Updated customer record.

    Raises:
        HTTPException: If customer not found.

    Example:
        >>> PUT /api/v1/customers/c29c3fb0-68ed-4f3d-b12c-884c2b83feca
        >>> {"name": "John Smith", "preferred_stylist": "Jane"}
    """
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with id {customer_id} not found",
        )

    # Update only provided fields
    update_data = customer_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)

    await db.commit()
    await db.refresh(customer)

    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a customer.

    Args:
        customer_id: Customer ID (UUID).
        db: Database session.

    Raises:
        HTTPException: If customer not found.

    Note:
        This is a hard delete. Consider soft delete for production.

    Example:
        >>> DELETE /api/v1/customers/c29c3fb0-68ed-4f3d-b12c-884c2b83feca
    """
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with id {customer_id} not found",
        )

    await db.delete(customer)
    await db.commit()
