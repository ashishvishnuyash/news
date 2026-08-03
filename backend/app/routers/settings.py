"""
Site Settings Router: Public read access for site configurations (motto, breaking news, categories, feature flags)
and Super Admin control to update settings.
"""
from typing import List, Dict, Any
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import SiteSetting, User
from app.schemas import SiteSettingResponse, SiteSettingCreate, SiteSettingsBatchUpdate
from app.auth import require_role

router = APIRouter(prefix="/api/settings", tags=["Site Settings"])

ALLOWED_SETTING_KEYS = {
    "site_name", "site_motto", "est_year", "edition_number", "breaking_news",
    "breaking_active", "categories", "features",
}


@router.get("", response_model=Dict[str, Any])
async def get_all_settings(db: AsyncSession = Depends(get_db)):
    """Fetch all site settings as a key-value dict for the application header & config."""
    result = await db.execute(select(SiteSetting))
    settings_list = result.scalars().all()
    
    settings_dict = {}
    for item in settings_list:
        try:
            # Try parsing JSON values if applicable (e.g. categories array, features object)
            settings_dict[item.key] = json.loads(item.value)
        except Exception:
            settings_dict[item.key] = item.value
            
    return settings_dict


@router.get("/{key}", response_model=SiteSettingResponse)
async def get_setting_by_key(key: str, db: AsyncSession = Depends(get_db)):
    """Fetch specific site setting by key."""
    result = await db.execute(select(SiteSetting).filter(SiteSetting.key == key))
    setting = result.scalars().first()
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found.")
    return setting


@router.put("", response_model=Dict[str, Any])
async def update_settings_batch(
    payload: Dict[str, Any],
    current_user: User = Depends(require_role(["SUPER_ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """Batch update site settings (Super Admin only)."""
    unknown = set(payload) - ALLOWED_SETTING_KEYS
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown setting keys: {', '.join(sorted(unknown))}")
    if len(json.dumps(payload)) > 50_000:
        raise HTTPException(status_code=413, detail="Settings payload is too large")
    for key, value in payload.items():
        result = await db.execute(select(SiteSetting).filter(SiteSetting.key == key))
        setting = result.scalars().first()
        
        string_val = json.dumps(value)
        
        if setting:
            setting.value = string_val
        else:
            setting = SiteSetting(
                key=key,
                value=string_val,
                description=f"System setting for {key}"
            )
            db.add(setting)
            
    await db.commit()
    return await get_all_settings(db)
