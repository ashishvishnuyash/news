import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import SiteSetting


async def setting_value(db: AsyncSession, key: str, default: Any = None) -> Any:
    result = await db.execute(select(SiteSetting).filter(SiteSetting.key == key))
    setting = result.scalars().first()
    if not setting:
        return default
    try:
        return json.loads(setting.value)
    except (TypeError, json.JSONDecodeError):
        return setting.value


async def feature_enabled(db: AsyncSession, key: str, default: bool = True) -> bool:
    features = await setting_value(db, "features", {})
    if not isinstance(features, dict):
        return default
    value = features.get(key, default)
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)
