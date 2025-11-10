"""API routers for the barbershop booking system.

This module exports all API routers for inclusion in the main FastAPI app.
"""

from src.api.routers import barbers, bookings, customers, services

__all__ = ["barbers", "bookings", "customers", "services"]
