"""API models package initialization."""

from src.api.models.database import Booking, Customer, Service, StaffAvailability
from src.api.models.schemas import (
    BookingCreate,
    BookingResponse,
    BookingUpdate,
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
    ServiceCreate,
    ServiceResponse,
    ServiceUpdate,
)

__all__ = [
    # Database models
    "Customer",
    "Service",
    "Booking",
    "StaffAvailability",
    # Schemas
    "CustomerCreate",
    "CustomerUpdate",
    "CustomerResponse",
    "ServiceCreate",
    "ServiceUpdate",
    "ServiceResponse",
    "BookingCreate",
    "BookingUpdate",
    "BookingResponse",
]
