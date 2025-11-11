"""Utility script to list all data in the barbershop database.

This script displays customers, barbers, services, availability schedules,
and bookings in a formatted, easy-to-read manner.

Usage:
    python list_data.py
    python list_data.py --customers
    python list_data.py --barbers
    python list_data.py --services
    python list_data.py --availability
    python list_data.py --bookings
"""

import argparse
import asyncio
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.api.models.database import (
    Barber,
    BarberAvailability,
    Booking,
    Customer,
    Service,
)
from src.core.config import get_settings

settings = get_settings()


async def list_customers(session):
    """List all customers."""
    print("\n" + "=" * 80)
    print("👥 CUSTOMERS")
    print("=" * 80)

    result = await session.execute(select(Customer))
    customers = result.scalars().all()

    if not customers:
        print("  No customers found.")
        return

    for customer in customers:
        print(f"\n📋 {customer.name}")
        print(f"   ID: {customer.id}")
        print(f"   Email: {customer.email}")
        print(f"   Phone: {customer.phone}")
        print(f"   Member Since: {customer.created_at.strftime('%Y-%m-%d')}")


async def list_barbers(session):
    """List all barbers."""
    print("\n" + "=" * 80)
    print("💈 BARBERS")
    print("=" * 80)

    result = await session.execute(select(Barber))
    barbers = result.scalars().all()

    if not barbers:
        print("  No barbers found.")
        return

    for barber in barbers:
        specialties = barber.specialties if barber.specialties else []
        status = "✅ Active" if barber.is_active else "❌ Inactive"

        print(f"\n💇 {barber.name} ({status})")
        print(f"   ID: {barber.id}")
        print(f"   Email: {barber.email}")
        print(f"   Phone: {barber.phone}")
        print(f"   Specialties: {', '.join(specialties)}")


async def list_services(session):
    """List all services."""
    print("\n" + "=" * 80)
    print("✂️  SERVICES")
    print("=" * 80)

    result = await session.execute(select(Service))
    services = result.scalars().all()

    if not services:
        print("  No services found.")
        return

    for service in services:
        status = "✅ Active" if service.is_active else "❌ Inactive"
        print(f"\n{service.name} ({status})")
        print(f"   ID: {service.id}")
        print(f"   Category: {service.category}")
        print(f"   Duration: {service.duration_minutes} minutes")
        print(f"   Price: ${service.price:.2f}")
        if service.description:
            print(f"   Description: {service.description}")


async def list_availability(session):
    """List barber availability schedules."""
    print("\n" + "=" * 80)
    print("📅 BARBER AVAILABILITY")
    print("=" * 80)

    result = await session.execute(
        select(Barber, BarberAvailability)
        .join(BarberAvailability, Barber.id == BarberAvailability.barber_id)
        .order_by(Barber.name, BarberAvailability.day_of_week)
    )
    rows = result.all()

    if not rows:
        print("  No availability schedules found.")
        return

    current_barber = None
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for barber, availability in rows:
        if current_barber != barber.name:
            current_barber = barber.name
            print(f"\n💇 {barber.name}")

        day_name = days[availability.day_of_week]
        print(f"   {day_name:12} {availability.start_time} - {availability.end_time}")


async def list_bookings(session):
    """List all bookings."""
    print("\n" + "=" * 80)
    print("📆 BOOKINGS")
    print("=" * 80)

    result = await session.execute(
        select(Booking, Customer, Service, Barber)
        .join(Customer, Booking.customer_id == Customer.id)
        .join(Service, Booking.service_id == Service.id)
        .outerjoin(Barber, Booking.barber_id == Barber.id)
        .order_by(Booking.start_time.desc())
    )
    rows = result.all()

    if not rows:
        print("  No bookings found.")
        return

    for booking, customer, service, barber in rows:
        status_emoji = {
            "pending": "🟡",
            "confirmed": "🟢",
            "cancelled": "🔴",
            "completed": "✅",
            "no_show": "❌",
        }
        status = f"{status_emoji.get(booking.status, '⚪')} {booking.status.upper()}"

        print(f"\n{status}")
        print(f"   Booking ID: {booking.id}")
        print(f"   Customer: {customer.name} ({customer.phone})")
        print(f"   Service: {service.name} (${service.price:.2f})")
        print(f"   Barber: {barber.name if barber else 'Not assigned'}")
        print(f"   Start: {booking.start_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"   End: {booking.end_time.strftime('%Y-%m-%d %H:%M')}")
        if booking.notes:
            print(f"   Notes: {booking.notes}")
        print(f"   Created: {booking.created_at.strftime('%Y-%m-%d %H:%M')}")


async def main():
    """Main function to list database contents."""
    parser = argparse.ArgumentParser(
        description="List barbershop database contents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--customers", action="store_true", help="List only customers")
    parser.add_argument("--barbers", action="store_true", help="List only barbers")
    parser.add_argument("--services", action="store_true", help="List only services")
    parser.add_argument("--availability", action="store_true", help="List only barber availability")
    parser.add_argument("--bookings", action="store_true", help="List only bookings")

    args = parser.parse_args()

    # If no specific flag is set, show everything
    show_all = not any(
        [args.customers, args.barbers, args.services, args.availability, args.bookings]
    )

    # Create database connection
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    print("\n🔍 Barbershop Database Contents")
    print(f"📊 Database: {settings.database_url.split(':///')[-1]}")
    print(f"⏰ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    async with async_session() as session:
        if show_all or args.customers:
            await list_customers(session)

        if show_all or args.barbers:
            await list_barbers(session)

        if show_all or args.services:
            await list_services(session)

        if show_all or args.availability:
            await list_availability(session)

        if show_all or args.bookings:
            await list_bookings(session)

    print("\n" + "=" * 80)
    print("✅ Complete!")
    print("=" * 80 + "\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
