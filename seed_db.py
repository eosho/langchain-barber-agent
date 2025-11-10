"""Database seed script for barbershop application.

This script loads data from seed_data.yaml and populates the database
with services, barbers, customers, and availability schedules.

Usage:
    uv run python seed_db.py
    uv run python seed_db.py --clear  # Clear existing data first
"""

import argparse
import asyncio
from pathlib import Path

import yaml
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.models.database import Barber, BarberAvailability, Base, Customer, Service


async def clear_database(session: AsyncSession) -> None:
    """Clear all data from the database.

    Args:
        session: Database session.
    """
    print("🗑️  Clearing existing data...")

    # Delete in order to respect foreign keys
    await session.execute(delete(BarberAvailability))
    await session.execute(delete(Customer))
    await session.execute(delete(Barber))
    await session.execute(delete(Service))

    await session.commit()
    print("✅ Database cleared")


async def seed_services(session: AsyncSession, services_data: list[dict]) -> dict[str, str]:
    """Seed services into the database.

    Args:
        session: Database session.
        services_data: List of service dictionaries.

    Returns:
        Mapping of service names to UUIDs.
    """
    print("\n📋 Seeding services...")
    service_map = {}

    for service_data in services_data:
        service = Service(
            name=service_data["name"],
            description=service_data["description"],
            duration_minutes=service_data["duration_minutes"],
            price=service_data["price"],
            category=service_data.get("category", "general"),
            is_active=service_data.get("is_active", True),
        )
        session.add(service)
        await session.flush()  # Get the ID
        service_map[service.name] = service.id
        print(f"  ✓ {service.name} (${service.price}, {service.duration_minutes}min)")

    await session.commit()
    print(f"✅ Seeded {len(services_data)} services")
    return service_map


async def seed_barbers(session: AsyncSession, barbers_data: list[dict]) -> dict[str, str]:
    """Seed barbers into the database.

    Args:
        session: Database session.
        barbers_data: List of barber dictionaries.

    Returns:
        Mapping of barber names to UUIDs.
    """
    print("\n💈 Seeding barbers...")
    barber_map = {}

    for barber_data in barbers_data:
        barber = Barber(
            name=barber_data["name"],
            email=barber_data["email"],
            phone=barber_data["phone"],
            specialties=barber_data.get("specialties", []),
            is_active=barber_data.get("is_active", True),
        )
        session.add(barber)
        await session.flush()  # Get the ID
        barber_map[barber.name] = barber.id
        print(f"  ✓ {barber.name} ({barber.email})")
        if barber.specialties:
            print(f"    Specialties: {', '.join(barber.specialties)}")

    await session.commit()
    print(f"✅ Seeded {len(barbers_data)} barbers")
    return barber_map


async def seed_customers(session: AsyncSession, customers_data: list[dict]) -> dict[str, str]:
    """Seed customers into the database.

    Args:
        session: Database session.
        customers_data: List of customer dictionaries.

    Returns:
        Mapping of customer emails to UUIDs.
    """
    print("\n👥 Seeding customers...")
    customer_map = {}

    for customer_data in customers_data:
        customer = Customer(
            name=customer_data["name"],
            email=customer_data.get("email"),
            phone=customer_data["phone"],
            # notes=customer_data.get("notes"),  # Add if Customer model has notes field
        )
        session.add(customer)
        await session.flush()  # Get the ID
        customer_map[customer.email if customer.email else customer.phone] = customer.id
        print(f"  ✓ {customer.name} ({customer.email or customer.phone})")
        if customer_data.get("notes"):
            print(f"    Notes: {customer_data['notes']}")

    await session.commit()
    print(f"✅ Seeded {len(customers_data)} customers")
    return customer_map


async def seed_barber_availability(
    session: AsyncSession, schedules_data: dict[str, dict], barber_map: dict[str, str]
) -> None:
    """Seed barber availability schedules.

    Args:
        session: Database session.
        schedules_data: Dictionary mapping barber names to their schedules.
        barber_map: Mapping of barber names to UUIDs.
    """
    print("\n📅 Seeding barber availability...")

    count = 0
    for barber_name, schedule in schedules_data.items():
        if barber_name not in barber_map:
            print(f"  ⚠️  Warning: Barber '{barber_name}' not found, skipping schedule")
            continue

        barber_id = barber_map[barber_name]

        for day_str, hours in schedule.items():
            day_of_week = int(day_str)
            start_time_str = hours["start"]  # Keep as string
            end_time_str = hours["end"]  # Keep as string

            availability = BarberAvailability(
                barber_id=barber_id,
                day_of_week=day_of_week,
                start_time=start_time_str,
                end_time=end_time_str,
                is_available=True,
            )
            session.add(availability)
            count += 1

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        working_days = [days[int(d)] for d in schedule]
        print(f"  ✓ {barber_name}: {', '.join(working_days)}")

    await session.commit()
    print(f"✅ Seeded {count} availability slots")


async def load_seed_data(file_path: Path) -> dict:
    """Load seed data from YAML file.

    Args:
        file_path: Path to YAML file.

    Returns:
        Parsed seed data dictionary.
    """
    print(f"📖 Loading seed data from {file_path}")

    with open(file_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    print("✅ Seed data loaded")
    return data


async def main(clear_existing: bool = False) -> None:
    """Run database seeding.

    Args:
        clear_existing: Whether to clear existing data first.
    """
    print("🌱 Starting database seed...")
    print("=" * 50)

    # Load seed data
    seed_file = Path(__file__).parent / "seed_data.yaml"
    if not seed_file.exists():
        print(f"❌ Error: Seed file not found at {seed_file}")
        return

    data = await load_seed_data(seed_file)

    # Create database engine
    from src.core.config import get_settings

    settings = get_settings()

    # Convert SQLite URL for async if needed
    db_url = settings.database_url
    if db_url.startswith("sqlite://"):
        db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")

    engine = create_async_engine(db_url, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Clear existing data if requested
        if clear_existing:
            await clear_database(session)

        # Seed all data
        service_map = await seed_services(session, data.get("services", []))
        barber_map = await seed_barbers(session, data.get("barbers", []))
        customer_map = await seed_customers(session, data.get("customers", []))

        # Seed availability schedules
        schedules = data.get("barber_schedules", {})
        await seed_barber_availability(session, schedules, barber_map)

    await engine.dispose()

    print("\n" + "=" * 50)
    print("✅ Database seeding complete!")
    print("\n📊 Summary:")
    print(f"  - Services: {len(service_map)}")
    print(f"  - Barbers: {len(barber_map)}")
    print(f"  - Customers: {len(customer_map)}")

    print("\n💡 You can now:")
    print("  - Start the API: uv run poe dev-api")
    print("  - Run the agent: uv run python run.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed barbershop database")
    parser.add_argument("--clear", action="store_true", help="Clear existing data before seeding")
    args = parser.parse_args()

    asyncio.run(main(clear_existing=args.clear))
