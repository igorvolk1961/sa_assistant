"""Reset the local database: truncate all app tables and re-seed roles/owner.

Refuses to run when APP_ENV=production.
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.services.bootstrap import bootstrap  # noqa: E402


async def main() -> None:
    settings = get_settings()
    if settings.app_env == "production":
        print("Refusing to reset the database when APP_ENV=production")
        raise SystemExit(1)

    async with engine.begin() as conn:
        tables = (
            await conn.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
                )
            )
        ).scalars().all()
        if tables:
            quoted = ", ".join(f'"{name}"' for name in tables)
            await conn.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))
        print(f"Truncated {len(tables)} tables")

    await bootstrap()
    print("Re-seeded roles and service owner")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
