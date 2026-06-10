from typing import Dict, List, Optional
from datetime import datetime, date
from pydantic import BaseModel

from app.ingredients import get_ingredient_by_id


class IntakeEntry(BaseModel):
    ingredient_id: str
    grams: float


class DailyIntake(BaseModel):
    profile_id: str
    date: str
    entries: List[IntakeEntry]
    total_calories: float = 0.0
    total_protein: float = 0.0
    total_carbs: float = 0.0
    total_fat: float = 0.0


class DeviationItem(BaseModel):
    nutrient: str
    recommended: float
    actual: float
    deviation_pct: float
    is_highlighted: bool


class DeviationAnalysis(BaseModel):
    date: str
    deviations: List[DeviationItem]
    has_high_deviation: bool


DEVIATION_THRESHOLD_PCT = 20.0

intake_db: Dict[str, Dict[str, DailyIntake]] = {}


def _get_date_str(d: date | datetime | str) -> str:
    if isinstance(d, str):
        return d
    if isinstance(d, datetime):
        return d.strftime("%Y-%m-%d")
    return d.strftime("%Y-%m-%d")


def add_intake(profile_id: str, intake_date: date | datetime | str, entries: List[IntakeEntry]) -> DailyIntake:
    date_str = _get_date_str(intake_date)

    if profile_id not in intake_db:
        intake_db[profile_id] = {}

    total_cal = 0.0
    total_prot = 0.0
    total_carb = 0.0
    total_fat = 0.0

    for entry in entries:
        ing = get_ingredient_by_id(entry.ingredient_id)
        if ing:
            factor = entry.grams / 100.0
            total_cal += ing.calories_per_100g * factor
            total_prot += ing.protein_per_100g * factor
            total_carb += ing.carbs_per_100g * factor
            total_fat += ing.fat_per_100g * factor

    daily = DailyIntake(
        profile_id=profile_id,
        date=date_str,
        entries=entries,
        total_calories=round(total_cal, 1),
        total_protein=round(total_prot, 1),
        total_carbs=round(total_carb, 1),
        total_fat=round(total_fat, 1),
    )

    intake_db[profile_id][date_str] = daily
    return daily


def get_intake(profile_id: str, intake_date: date | datetime | str) -> Optional[DailyIntake]:
    date_str = _get_date_str(intake_date)
    if profile_id not in intake_db:
        return None
    return intake_db[profile_id].get(date_str)


def get_intake_range(profile_id: str, start_date: date, end_date: date) -> List[DailyIntake]:
    results: List[DailyIntake] = []
    if profile_id not in intake_db:
        return results

    from datetime import timedelta
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        if date_str in intake_db[profile_id]:
            results.append(intake_db[profile_id][date_str])
        current += timedelta(days=1)
    return results


def analyze_deviation(
    recommended_calories: float,
    recommended_protein: float,
    recommended_carbs: float,
    recommended_fat: float,
    actual_intake: DailyIntake,
    threshold_pct: float = DEVIATION_THRESHOLD_PCT,
) -> DeviationAnalysis:
    deviations: List[DeviationItem] = []
    has_high = False

    nutrients = [
        ("热量 (kcal)", recommended_calories, actual_intake.total_calories),
        ("蛋白质 (g)", recommended_protein, actual_intake.total_protein),
        ("碳水化合物 (g)", recommended_carbs, actual_intake.total_carbs),
        ("脂肪 (g)", recommended_fat, actual_intake.total_fat),
    ]

    for name, rec, actual in nutrients:
        if rec > 0:
            dev_pct = (actual - rec) / rec * 100
        else:
            dev_pct = 0.0

        is_high = abs(dev_pct) > threshold_pct
        if is_high:
            has_high = True

        deviations.append(DeviationItem(
            nutrient=name,
            recommended=round(rec, 1),
            actual=round(actual, 1),
            deviation_pct=round(dev_pct, 1),
            is_highlighted=is_high,
        ))

    return DeviationAnalysis(
        date=actual_intake.date,
        deviations=deviations,
        has_high_deviation=has_high,
    )


def analyze_weekly_deviation(
    recommended_calories: float,
    recommended_protein: float,
    recommended_carbs: float,
    recommended_fat: float,
    weekly_intakes: List[DailyIntake],
    threshold_pct: float = DEVIATION_THRESHOLD_PCT,
) -> Dict[str, DeviationAnalysis]:
    results: Dict[str, DeviationAnalysis] = {}
    for intake in weekly_intakes:
        results[intake.date] = analyze_deviation(
            recommended_calories,
            recommended_protein,
            recommended_carbs,
            recommended_fat,
            intake,
            threshold_pct,
        )
    return results
