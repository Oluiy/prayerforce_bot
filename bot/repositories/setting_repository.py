"""Database access for admin-editable settings. Only overrides are stored."""
from database.prisma_connect import db


async def get_all() -> dict[str, str]:
    rows = await db.setting.find_many()
    return {row.key: row.value for row in rows}


async def set(key: str, value: str, updated_by: str | None = None):
    return await db.setting.upsert(
        where={"key": key},
        data={
            "create": {"key": key, "value": value, "updatedBy": updated_by},
            "update": {"value": value, "updatedBy": updated_by},
        },
    )


async def delete(key: str):
    await db.setting.delete_many(where={"key": key})
