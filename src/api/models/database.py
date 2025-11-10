"""Database models for the barbershop booking system.

This module defines SQLAlchemy ORM models for all database entities
including customers, services, bookings, barbers, and staff.

Example:
    >>> from src.api.models.database import Booking
    >>> booking = Booking(customer_id=1, service_id=2, start_time=datetime.now())
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


def utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(UTC)


class Customer(Base):
    """Customer model for storing customer information.

    Attributes:
        id: Primary key (UUID).
        name: Customer's full name.
        phone: Customer's phone number (unique).
        email: Customer's email address (optional).
        created_at: Timestamp of customer creation.
        updated_at: Timestamp of last update.
        bookings: Relationship to customer's bookings.
    """

    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4()), index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    bookings: Mapped[list["Booking"]] = relationship("Booking", back_populates="customer")

    def __repr__(self) -> str:
        """String representation of customer."""
        return f"<Customer(id={self.id}, name='{self.name}', phone='{self.phone}')>"


class Service(Base):
    """Service model for available barbershop services.

    Attributes:
        id: Primary key (UUID).
        name: Service name.
        description: Detailed service description.
        duration_minutes: Duration of service in minutes.
        price: Service price.
        category: Service category (haircut, grooming, package).
        is_active: Whether service is currently offered.
        created_at: Timestamp of service creation.
        updated_at: Timestamp of last update.
        bookings: Relationship to bookings using this service.
    """

    __tablename__ = "services"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4()), index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    bookings: Mapped[list["Booking"]] = relationship("Booking", back_populates="service")

    def __repr__(self) -> str:
        """String representation of service."""
        return f"<Service(id={self.id}, name='{self.name}', price=${self.price})>"


class Barber(Base):
    """Barber model for staff members.

    Attributes:
        id: Primary key (UUID).
        name: Barber's full name.
        email: Barber's email address (unique).
        phone: Barber's phone number.
        specialties: List of specialties (stored as JSON).
        is_active: Whether barber is currently working.
        created_at: Timestamp of barber creation.
        updated_at: Timestamp of last update.
        availability: Relationship to barber's availability schedule.
        bookings: Relationship to barber's bookings.
    """

    __tablename__ = "barbers"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4()), index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    specialties: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    availability: Mapped[list["BarberAvailability"]] = relationship(
        "BarberAvailability", back_populates="barber", cascade="all, delete-orphan"
    )
    bookings: Mapped[list["Booking"]] = relationship("Booking", back_populates="barber")

    def __repr__(self) -> str:
        """String representation of barber."""
        return f"<Barber(id={self.id}, name='{self.name}', email='{self.email}')>"


class BarberAvailability(Base):
    """Barber availability model for defining weekly schedules.

    Attributes:
        id: Primary key (UUID).
        barber_id: Foreign key to barber (UUID).
        day_of_week: Day of week (0=Monday, 6=Sunday).
        start_time: Start time (HH:MM format or time object).
        end_time: End time (HH:MM format or time object).
        is_available: Whether barber is available on this day/time.
        created_at: Timestamp of creation.
        updated_at: Timestamp of last update.
        barber: Relationship to barber.
    """

    __tablename__ = "barber_availability"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4()), index=True
    )
    barber_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("barbers.id"), nullable=False, index=True
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 0-6
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM format
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM format
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    barber: Mapped["Barber"] = relationship("Barber", back_populates="availability")

    def __repr__(self) -> str:
        """String representation of availability."""
        return (
            f"<BarberAvailability(id={self.id}, barber_id={self.barber_id}, "
            f"day_of_week={self.day_of_week}, start_time='{self.start_time}', end_time='{self.end_time}')>"
        )


class Booking(Base):
    """Booking model for customer appointments.

    Attributes:
        id: Primary key (UUID).
        customer_id: Foreign key to customer (UUID).
        service_id: Foreign key to service (UUID).
        barber_id: Foreign key to barber (UUID, optional).
        start_time: Booking start time.
        end_time: Booking end time.
        status: Booking status (confirmed, cancelled, completed, no_show).
        notes: Optional booking notes or special requests.
        created_at: Timestamp of booking creation.
        updated_at: Timestamp of last update.
        customer: Relationship to customer.
        service: Relationship to service.
        barber: Relationship to barber.
    """

    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4()), index=True
    )
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id"), nullable=False, index=True
    )
    service_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("services.id"), nullable=False, index=True
    )
    barber_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("barbers.id"), nullable=True, index=True
    )
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="confirmed", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="bookings")
    service: Mapped["Service"] = relationship("Service", back_populates="bookings")
    barber: Mapped["Barber | None"] = relationship("Barber", back_populates="bookings")

    def __repr__(self) -> str:
        """String representation of booking."""
        return (
            f"<Booking(id={self.id}, customer_id={self.customer_id}, "
            f"service_id={self.service_id}, barber_id={self.barber_id}, "
            f"start_time={self.start_time}, status='{self.status}')>"
        )


class StaffAvailability(Base):
    """Staff availability model for defining business hours.

    Attributes:
        id: Primary key.
        day_of_week: Day of week (0=Monday, 6=Sunday).
        start_time: Opening time.
        end_time: Closing time.
        is_available: Whether staff is available on this day.
        created_at: Timestamp of creation.
        updated_at: Timestamp of last update.
    """

    __tablename__ = "staff_availability"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 0-6
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM format
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM format
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    def __repr__(self) -> str:
        """String representation of availability."""
        return (
            f"<StaffAvailability(id={self.id}, day_of_week={self.day_of_week}, "
            f"start_time='{self.start_time}', end_time='{self.end_time}')>"
        )
