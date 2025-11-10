"""Pydantic schemas for API request/response validation.

This module defines Pydantic models for data validation and serialization
in the FastAPI application.

Example:
    >>> from src.api.models.schemas import BookingCreate
    >>> booking = BookingCreate(
    ...     customer_id=1,
    ...     service_id=2,
    ...     start_time=datetime.now()
    ... )
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

# ============================================================================
# Customer Schemas
# ============================================================================


class CustomerBase(BaseModel):
    """Base customer schema with common attributes.

    Attributes:
        name: Customer's full name.
        phone: Customer's phone number.
        email: Optional email address.
    """

    name: str = Field(..., min_length=2, max_length=100, description="Customer's full name")
    phone: str = Field(
        ...,
        pattern=r"^\+?[\d\-\s().]+$",
        min_length=7,
        max_length=20,
        description="Customer's phone number",
    )
    email: EmailStr | None = Field(None, description="Customer's email address")


class CustomerCreate(CustomerBase):
    """Schema for creating a new customer."""


class CustomerUpdate(BaseModel):
    """Schema for updating customer information.

    All fields are optional to allow partial updates.
    """

    name: str | None = Field(None, min_length=2, max_length=100)
    phone: str | None = Field(None, pattern=r"^\+?[\d\-\s().]+$", min_length=7, max_length=20)
    email: EmailStr | None = None


class CustomerResponse(CustomerBase):
    """Schema for customer responses.

    Attributes:
        id: Customer ID (UUID).
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================================
# Barber Schemas
# ============================================================================


class BarberBase(BaseModel):
    """Base barber schema with common attributes.

    Attributes:
        name: Barber's full name.
        email: Barber's email address.
        phone: Barber's phone number.
        specialties: List of specialties or skills.
    """

    name: str = Field(..., min_length=2, max_length=100, description="Barber's full name")
    email: EmailStr = Field(..., description="Barber's email address")
    phone: str = Field(
        ...,
        pattern=r"^\+?[\d\-\s().]+$",
        min_length=7,
        max_length=20,
        description="Barber's phone number",
    )
    specialties: list[str] | None = Field(default=None, description="List of specialties")


class BarberCreate(BarberBase):
    """Schema for creating a new barber."""


class BarberUpdate(BaseModel):
    """Schema for updating barber information.

    All fields are optional to allow partial updates.
    """

    name: str | None = Field(None, min_length=2, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, pattern=r"^\+?[\d\-\s().]+$", min_length=7, max_length=20)
    specialties: list[str] | None = None
    is_active: bool | None = None


class BarberResponse(BarberBase):
    """Schema for barber responses.

    Attributes:
        id: Barber ID (UUID).
        is_active: Whether barber is currently active.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: str
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ============================================================================
# Service Schemas
# ============================================================================


class ServiceBase(BaseModel):
    """Base service schema with common attributes.

    Attributes:
        name: Service name.
        description: Service description.
        duration_minutes: Duration in minutes.
        price: Service price.
        category: Service category.
    """

    name: str = Field(..., min_length=2, max_length=100, description="Service name")
    description: str = Field(..., min_length=10, description="Service description")
    duration_minutes: int = Field(..., gt=0, le=240, description="Duration in minutes")
    price: float = Field(..., gt=0, description="Service price")
    category: str = Field(..., description="Service category")


class ServiceCreate(ServiceBase):
    """Schema for creating a new service."""

    is_active: bool = Field(default=True, description="Whether service is active")


class ServiceUpdate(BaseModel):
    """Schema for updating service information.

    All fields are optional to allow partial updates.
    """

    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = Field(None, min_length=10)
    duration_minutes: int | None = Field(None, gt=0, le=240)
    price: float | None = Field(None, gt=0)
    category: str | None = None
    is_active: bool | None = None


class ServiceResponse(ServiceBase):
    """Schema for service responses.

    Attributes:
        id: Service ID (UUID).
        is_active: Whether service is currently offered.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================================
# Booking Schemas
# ============================================================================


class BookingBase(BaseModel):
    """Base booking schema with common attributes.

    Attributes:
        customer_id: ID of the customer (UUID).
        service_id: ID of the service (UUID).
        barber_id: Optional ID of the barber (UUID).
        start_time: Booking start time.
        notes: Optional notes or special requests.
    """

    customer_id: str = Field(..., min_length=36, max_length=36, description="Customer ID (UUID)")
    service_id: str = Field(..., min_length=36, max_length=36, description="Service ID (UUID)")
    barber_id: str | None = Field(
        None, min_length=36, max_length=36, description="Barber ID (UUID)"
    )
    start_time: datetime = Field(..., description="Booking start time")
    notes: str | None = Field(None, max_length=500, description="Optional booking notes")


class BookingCreate(BookingBase):
    """Schema for creating a new booking.

    The end_time is calculated automatically based on service duration.
    """

    @field_validator("start_time")
    @classmethod
    def validate_future_time(cls, v: datetime) -> datetime:
        """Validate that booking time is in the future.

        Args:
            v: Start time to validate.

        Returns:
            Validated start time.

        Raises:
            ValueError: If start time is in the past.
        """
        if v < datetime.now():
            raise ValueError("Booking time must be in the future")
        return v


class BookingUpdate(BaseModel):
    """Schema for updating booking information.

    All fields are optional to allow partial updates.
    """

    barber_id: str | None = Field(None, min_length=36, max_length=36)
    start_time: datetime | None = None
    status: str | None = Field(None, pattern=r"^(confirmed|cancelled|completed|no_show)$")
    notes: str | None = Field(None, max_length=500)

    @field_validator("start_time")
    @classmethod
    def validate_future_time(cls, v: datetime | None) -> datetime | None:
        """Validate that new booking time is in the future."""
        if v is not None and v < datetime.now():
            raise ValueError("Booking time must be in the future")
        return v


class BookingResponse(BookingBase):
    """Schema for booking responses.

    Attributes:
        id: Booking ID (UUID).
        end_time: Booking end time.
        status: Booking status.
        customer: Customer information.
        service: Service information.
        barber: Optional barber information.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: str
    end_time: datetime
    status: str
    customer: CustomerResponse
    service: ServiceResponse
    barber: BarberResponse | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BookingListResponse(BaseModel):
    """Schema for booking list responses without nested relationships."""

    id: str
    customer_id: str
    service_id: str
    barber_id: str | None
    start_time: datetime
    end_time: datetime
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================================
# Availability Schemas
# ============================================================================


class AvailabilityQuery(BaseModel):
    """Schema for querying available time slots.

    Attributes:
        date: Date to check availability in YYYY-MM-DD format.
        service_id: Service ID (UUID) to check.
        preferred_stylist: Optional preferred stylist name.
    """

    date: str = Field(..., description="Date to check availability (YYYY-MM-DD)")
    service_id: str = Field(..., min_length=36, max_length=36, description="Service ID (UUID)")
    preferred_stylist: str | None = Field(None, description="Optional preferred stylist name")


class TimeSlot(BaseModel):
    """Schema for an available time slot.

    Attributes:
        start_time: Slot start time.
        end_time: Slot end time.
        available: Whether slot is available.
    """

    start_time: datetime
    end_time: datetime
    available: bool = True


class AvailabilityResponse(BaseModel):
    """Schema for availability query responses.

    Attributes:
        date: Queried date.
        service_id: Queried service ID (UUID).
        slots: List of time slots.
    """

    date: datetime
    service_id: str
    slots: list[TimeSlot]


# ============================================================================
# Error Schemas
# ============================================================================


class ErrorResponse(BaseModel):
    """Schema for error responses.

    Attributes:
        error: Error type or code.
        message: Human-readable error message.
        details: Optional additional error details.
    """

    error: str
    message: str
    details: dict[str, str] | None = None


# ============================================================================
# Health Check Schema
# ============================================================================


class HealthResponse(BaseModel):
    """Schema for health check responses.

    Attributes:
        status: Service status.
        version: Application version.
        timestamp: Current timestamp.
    """

    status: str = "healthy"
    version: str
    timestamp: datetime
