"""Seed the database with default categories.

Usage:
    python seed_categories.py
    python seed_categories.py seed-categories   # if more commands are added later
"""

import asyncio
from uuid import UUID

import typer
from sqlalchemy.dialects.postgresql import insert

from app.db.session import async_session_maker
from app.places.models import CategoryModel

app = typer.Typer(help="Database seeding commands.")

CATEGORIES: dict[str, str] = {
    "550e8400-e29b-41d4-a716-446655440001": "Cafe",
    "550e8400-e29b-41d4-a716-446655440002": "Restaurant",
    "550e8400-e29b-41d4-a716-446655440003": "Bar",
    "550e8400-e29b-41d4-a716-446655440004": "Bakery",
    "550e8400-e29b-41d4-a716-446655440005": "Street food",
    "550e8400-e29b-41d4-a716-446655440006": "Museum",
    "550e8400-e29b-41d4-a716-446655440007": "Park",
    "550e8400-e29b-41d4-a716-446655440008": "Shopping",
}


async def _seed_categories() -> int:
    """Insert categories, skipping any that already exist. Returns inserted count."""
    values = [
        {"id": UUID(category_id), "name": name}
        for category_id, name in CATEGORIES.items()
    ]

    stmt = (
        insert(CategoryModel)
        .values(values)
        # Skips rows conflicting on the primary key OR the unique `name`,
        # so the command is safe to run multiple times.
        .on_conflict_do_nothing()
        .returning(CategoryModel.id)
    )

    async with async_session_maker() as session:
        result = await session.execute(stmt)
        inserted = len(result.scalars().all())
        await session.commit()

    return inserted


@app.command()
def seed_categories() -> None:
    """Seed the categories table with default values."""
    inserted = asyncio.run(_seed_categories())
    skipped = len(CATEGORIES) - inserted
    typer.echo(f"Categories seeded: {inserted} inserted, {skipped} already existed.")


if __name__ == "__main__":
    app()
