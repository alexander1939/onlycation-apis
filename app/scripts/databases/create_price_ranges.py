from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.cores.db import async_session
from app.models.common.status import Status
from app.models.common.educational_level import EducationalLevel
from app.models.common.price_range import PriceRange

async def create_prices_range():
    async with async_session() as db:  # Correcta inicialización de sesión
        try:
            result = await db.execute(select(PriceRange))
            prices_ranges = result.scalars().all()

            if not prices_ranges:
                # Obtener el status "active"
                status_result = await db.execute(
                    select(Status).where(Status.name == "active")
                )
                active_status = status_result.scalars().first()

                if not active_status:
                    print("Error: 'active' status not found. Please create statuses first.")
                    return

                # Obtener niveles educativos
                educational_levels_result = await db.execute(select(EducationalLevel))
                educational_levels = {level.name: level.id for level in educational_levels_result.scalars().all()}

                if not educational_levels:
                    print("Error: No educational levels found. Please create educational levels first.")
                    return


                prices_ranges_list = []

                if "Preparatoria" in educational_levels:
                    prices_ranges_list.append(
                        PriceRange(
                            educational_level_id=educational_levels["Preparatoria"],
                            minimum_price=100.00,
                            maximum_price=800.00,
                            status_id=active_status.id
                        )
                    )

                if "Universidad" in educational_levels:
                    prices_ranges_list.append(
                        PriceRange(
                            educational_level_id=educational_levels["Universidad"],
                            minimum_price=200.00,
                            maximum_price=1200.00,
                            status_id=active_status.id
                        )
                    )

                if "Posgrado" in educational_levels:
                    prices_ranges_list.append(
                        PriceRange(
                            educational_level_id=educational_levels["Posgrado"],
                            minimum_price=300.00,
                            maximum_price=1500.00,
                         status_id=active_status.id
                        )
                    )


                db.add_all(prices_ranges_list)
                await db.commit()
                print(f"✅ Successfully created {len(prices_ranges_list)} price ranges for educational levels.")

                for level_name, level_id in educational_levels.items():
                    level_ranges = [pr for pr in prices_ranges_list if pr.educational_level_id == level_id]
                    print(f" - {level_name}: {len(level_ranges)} price ranges created.")

            else:
                print("ℹ️ Price ranges already exist in the database.")

        except Exception as e:
            await db.rollback()
            print(f"❌ Error creating price ranges: {str(e)}")