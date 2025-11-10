"""Custom exceptions for the barbershop booking agent.

This module defines application-specific exceptions that provide
clear error messages and proper HTTP status codes for API responses.

Example:
    >>> from src.core.exceptions import BookingConflictError
    >>> raise BookingConflictError("Time slot already booked")
"""


class BarbershopError(Exception):
    """Base exception for all barbershop application errors.

    All custom exceptions should inherit from this base class.

    Attributes:
        message: Human-readable error message.
        details: Optional additional error details.
    """

    def __init__(self, message: str, details: dict[str, str] | None = None) -> None:
        """Initialize exception with message and optional details.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error context.
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ConfigurationError(BarbershopError):
    """Exception raised for configuration-related errors.

    Raised when required configuration is missing or invalid.
    """

    pass


class DatabaseError(BarbershopError):
    """Exception raised for database-related errors.

    Raised when database operations fail or constraints are violated.
    """

    pass


# Booking-related exceptions


class BookingError(BarbershopError):
    """Base exception for booking-related errors."""

    pass


class BookingNotFoundError(BookingError):
    """Exception raised when a booking cannot be found.

    Raised when attempting to retrieve, update, or cancel a non-existent booking.
    """

    pass


class BookingConflictError(BookingError):
    """Exception raised when a booking conflicts with an existing booking.

    Raised when attempting to create a booking for a time slot that's already taken.
    """

    pass


class InvalidBookingTimeError(BookingError):
    """Exception raised when booking time is invalid.

    Raised when:
    - Booking time is in the past
    - Booking time is outside business hours
    - Booking is too far in advance
    - Same-day booking is after cutoff time
    """

    pass


class CancellationPolicyViolationError(BookingError):
    """Exception raised when cancellation violates policy.

    Raised when attempting to cancel a booking without sufficient notice
    as defined by the cancellation policy.
    """

    pass


# Customer-related exceptions


class CustomerError(BarbershopError):
    """Base exception for customer-related errors."""

    pass


class CustomerNotFoundError(CustomerError):
    """Exception raised when a customer cannot be found.

    Raised when attempting to retrieve a non-existent customer.
    """

    pass


class DuplicateCustomerError(CustomerError):
    """Exception raised when attempting to create a duplicate customer.

    Raised when a customer with the same phone number or email already exists.
    """

    pass


# Service-related exceptions


class ServiceError(BarbershopError):
    """Base exception for service-related errors."""

    pass


class ServiceNotFoundError(ServiceError):
    """Exception raised when a service cannot be found.

    Raised when attempting to book a non-existent service.
    """

    pass


# Agent-related exceptions


class AgentError(BarbershopError):
    """Base exception for AI agent-related errors."""

    pass


class AgentTimeoutError(AgentError):
    """Exception raised when agent execution exceeds timeout.

    Raised when the agent takes too long to complete its task.
    """

    pass


class AgentMaxIterationsError(AgentError):
    """Exception raised when agent exceeds maximum iterations.

    Raised when the agent loops too many times without reaching a conclusion.
    """

    pass


class ToolExecutionError(AgentError):
    """Exception raised when a tool execution fails.

    Raised when a tool called by the agent encounters an error.
    """

    pass


# Validation exceptions


class ValidationError(BarbershopError):
    """Exception raised for input validation errors.

    Raised when user input doesn't meet validation requirements.
    """

    pass


class InvalidPhoneNumberError(ValidationError):
    """Exception raised when phone number format is invalid."""

    pass


class InvalidEmailError(ValidationError):
    """Exception raised when email format is invalid."""

    pass


class InvalidDateTimeError(ValidationError):
    """Exception raised when date or time format is invalid."""

    pass
