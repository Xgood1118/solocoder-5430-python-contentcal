from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"


class ActivityLevel(str, Enum):
    SEDENTARY = "sedentary"
    LIGHT = "light"
    MODERATE = "moderate"
    HIGH = "high"


class Goal(str, Enum):
    FAT_LOSS = "fat_loss"
    MUSCLE_GAIN = "muscle_gain"
    MAINTENANCE = "maintenance"


class FlagType(str, Enum):
    ALLERGY_PEANUT = "allergy_peanut"
    ALLERGY_GLUTEN = "allergy_gluten"
    ALLERGY_LACTOSE = "allergy_lactose"
    ALLERGY_SEAFOOD = "allergy_seafood"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    HALAL = "halal"
    KOSHER = "kosher"


class SpecialCondition(str, Enum):
    NONE = "none"
    PREGNANT = "pregnant"
    LACTATING = "lactating"
    MENSTRUATING = "menstruating"


class ProfileCreate(BaseModel):
    name: str
    gender: Gender
    age: int = Field(ge=1, le=120)
    height: float = Field(gt=0, description="身高，单位：厘米")
    weight: float = Field(gt=0, description="体重，单位：公斤")
    activity_level: ActivityLevel
    goal: Goal
    flags: List[FlagType] = Field(default_factory=list)
    special_condition: SpecialCondition = SpecialCondition.NONE


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[Gender] = None
    age: Optional[int] = Field(default=None, ge=1, le=120)
    height: Optional[float] = Field(default=None, gt=0)
    weight: Optional[float] = Field(default=None, gt=0)
    activity_level: Optional[ActivityLevel] = None
    goal: Optional[Goal] = None
    flags: Optional[List[FlagType]] = None
    special_condition: Optional[SpecialCondition] = None


class WeightHistory(BaseModel):
    weight: float
    timestamp: datetime


class Profile(BaseModel):
    id: str
    name: str
    gender: Gender
    age: int
    height: float
    weight: float
    activity_level: ActivityLevel
    goal: Goal
    flags: List[FlagType]
    special_condition: SpecialCondition
    weight_history: List[WeightHistory] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
