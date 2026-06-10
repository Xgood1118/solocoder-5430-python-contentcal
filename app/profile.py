from typing import Dict, Optional
from datetime import datetime
import uuid

from app.models import Profile, ProfileCreate, ProfileUpdate, WeightHistory


profiles_db: Dict[str, Profile] = {}


def create_profile(data: ProfileCreate) -> Profile:
    profile_id = str(uuid.uuid4())
    now = datetime.now()
    profile = Profile(
        id=profile_id,
        name=data.name,
        gender=data.gender,
        age=data.age,
        height=data.height,
        weight=data.weight,
        activity_level=data.activity_level,
        goal=data.goal,
        flags=data.flags.copy(),
        special_condition=data.special_condition,
        weight_history=[WeightHistory(weight=data.weight, timestamp=now)],
        created_at=now,
        updated_at=now,
    )
    profiles_db[profile_id] = profile
    return profile


def get_profile(profile_id: str) -> Optional[Profile]:
    return profiles_db.get(profile_id)


def update_profile(profile_id: str, data: ProfileUpdate) -> Optional[Profile]:
    profile = profiles_db.get(profile_id)
    if not profile:
        return None

    update_data = data.model_dump(exclude_unset=True)
    weight_changed = "weight" in update_data and update_data["weight"] != profile.weight

    for key, value in update_data.items():
        setattr(profile, key, value)

    if weight_changed:
        profile.weight_history.append(
            WeightHistory(weight=data.weight, timestamp=datetime.now())
        )

    profile.updated_at = datetime.now()
    return profile


def delete_profile(profile_id: str) -> bool:
    if profile_id in profiles_db:
        del profiles_db[profile_id]
        return True
    return False


def list_profiles() -> list[Profile]:
    return list(profiles_db.values())
