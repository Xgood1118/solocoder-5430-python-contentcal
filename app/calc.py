from typing import Optional
from pydantic import BaseModel

from app.models import Profile, Gender, ActivityLevel, Goal, SpecialCondition


class Macronutrients(BaseModel):
    protein: float
    carbs: float
    fat: float


class Micronutrients(BaseModel):
    calcium_mg: float
    iron_mg: float
    vitamin_c_mg: float
    vitamin_d_iu: float
    vitamin_a_ug: float
    vitamin_b1_mg: float
    vitamin_b2_mg: float
    niacin_mg: float
    zinc_mg: float
    selenium_ug: float
    iodine_ug: float
    magnesium_mg: float


class CalculationResult(BaseModel):
    bmr: float
    tdee: float
    target_calories: float
    macronutrients: Macronutrients
    micronutrients: Micronutrients
    warnings: list[str] = []


ACTIVITY_FACTORS = {
    ActivityLevel.SEDENTARY: 1.2,
    ActivityLevel.LIGHT: 1.375,
    ActivityLevel.MODERATE: 1.55,
    ActivityLevel.HIGH: 1.725,
}

GOAL_ADJUSTMENTS = {
    Goal.FAT_LOSS: -500,
    Goal.MUSCLE_GAIN: 300,
    Goal.MAINTENANCE: 0,
}

MACRO_RATIOS = {
    Goal.FAT_LOSS: {"protein": 0.30, "carbs": 0.40, "fat": 0.30},
    Goal.MUSCLE_GAIN: {"protein": 0.25, "carbs": 0.50, "fat": 0.25},
    Goal.MAINTENANCE: {"protein": 0.20, "carbs": 0.50, "fat": 0.30},
}

KCAL_PER_GRAM_PROTEIN = 4.0
KCAL_PER_GRAM_CARBS = 4.0
KCAL_PER_GRAM_FAT = 9.0

MIN_AGE = 18
MAX_AGE = 65
MIN_BMI = 15.0
MAX_BMI = 40.0


def calculate_bmr(weight: float, height: float, age: int, gender: Gender) -> float:
    if gender == Gender.MALE:
        return 10 * weight + 6.25 * height - 5 * age + 5
    else:
        return 10 * weight + 6.25 * height - 5 * age - 161


def calculate_bmi(weight: float, height: float) -> float:
    height_m = height / 100.0
    return weight / (height_m * height_m)


def calculate_macros(calories: float, goal: Goal) -> Macronutrients:
    ratios = MACRO_RATIOS[goal]
    protein_kcal = calories * ratios["protein"]
    carbs_kcal = calories * ratios["carbs"]
    fat_kcal = calories * ratios["fat"]

    return Macronutrients(
        protein=round(protein_kcal / KCAL_PER_GRAM_PROTEIN, 1),
        carbs=round(carbs_kcal / KCAL_PER_GRAM_CARBS, 1),
        fat=round(fat_kcal / KCAL_PER_GRAM_FAT, 1),
    )


def calculate_micronutrients(
    gender: Gender,
    special_condition: SpecialCondition,
    age: int,
) -> Micronutrients:
    iron_mg = 12.0 if gender == Gender.MALE else 18.0
    if special_condition == SpecialCondition.MENSTRUATING:
        iron_mg = 20.0
    if special_condition in (SpecialCondition.PREGNANT, SpecialCondition.LACTATING):
        iron_mg = 25.0

    calcium_mg = 800.0
    if special_condition == SpecialCondition.PREGNANT:
        calcium_mg = 1000.0
    elif special_condition == SpecialCondition.LACTATING:
        calcium_mg = 1200.0

    vitamin_c_mg = 100.0
    if special_condition in (SpecialCondition.PREGNANT, SpecialCondition.LACTATING):
        vitamin_c_mg = 130.0

    vitamin_d_iu = 400.0
    vitamin_a_ug = 800.0 if gender == Gender.MALE else 700.0
    if special_condition == SpecialCondition.PREGNANT:
        vitamin_a_ug = 770.0
    elif special_condition == SpecialCondition.LACTATING:
        vitamin_a_ug = 1300.0

    vitamin_b1_mg = 1.4 if gender == Gender.MALE else 1.2
    vitamin_b2_mg = 1.4 if gender == Gender.MALE else 1.2
    niacin_mg = 14.0 if gender == Gender.MALE else 12.0

    zinc_mg = 12.5 if gender == Gender.MALE else 7.5
    if special_condition == SpecialCondition.PREGNANT:
        zinc_mg = 9.5
    elif special_condition == SpecialCondition.LACTATING:
        zinc_mg = 12.0

    selenium_ug = 60.0
    iodine_ug = 120.0
    if special_condition in (SpecialCondition.PREGNANT, SpecialCondition.LACTATING):
        iodine_ug = 230.0

    magnesium_mg = 350.0 if gender == Gender.MALE else 300.0

    return Micronutrients(
        calcium_mg=calcium_mg,
        iron_mg=iron_mg,
        vitamin_c_mg=vitamin_c_mg,
        vitamin_d_iu=vitamin_d_iu,
        vitamin_a_ug=vitamin_a_ug,
        vitamin_b1_mg=vitamin_b1_mg,
        vitamin_b2_mg=vitamin_b2_mg,
        niacin_mg=niacin_mg,
        zinc_mg=zinc_mg,
        selenium_ug=selenium_ug,
        iodine_ug=iodine_ug,
        magnesium_mg=magnesium_mg,
    )


def calculate_nutrition(profile: Profile) -> CalculationResult:
    warnings: list[str] = []

    if profile.age < MIN_AGE or profile.age > MAX_AGE:
        raise ValueError(
            f"年龄 {profile.age} 超出计算范围（{MIN_AGE}-{MAX_AGE}岁）。"
            f"本服务的营养计算公式仅适用于成年人群，"
            f"儿童和老年人的营养需求需由专业医师评估。"
        )

    bmi = calculate_bmi(profile.weight, profile.height)
    if bmi < MIN_BMI:
        warnings.append(
            f"BMI 为 {bmi:.1f}，低于 {MIN_BMI}，计算结果临床参考价值有限，"
            f"建议咨询专业医师或营养师。"
        )
    elif bmi > MAX_BMI:
        warnings.append(
            f"BMI 为 {bmi:.1f}，高于 {MAX_BMI}，计算结果临床参考价值有限，"
            f"建议咨询专业医师或营养师。"
        )

    if profile.special_condition == SpecialCondition.PREGNANT:
        warnings.append(
            "妊娠期女性的营养需求特殊，本计算仅作参考，"
            "请务必遵医嘱并定期产检。"
        )
    elif profile.special_condition == SpecialCondition.LACTATING:
        warnings.append(
            "哺乳期女性的营养需求特殊，本计算仅作参考，"
            "请咨询专业医师或营养师。"
        )

    bmr = calculate_bmr(profile.weight, profile.height, profile.age, profile.gender)
    activity_factor = ACTIVITY_FACTORS[profile.activity_level]
    tdee = bmr * activity_factor
    goal_adjustment = GOAL_ADJUSTMENTS[profile.goal]
    target_calories = tdee + goal_adjustment

    if target_calories < 1200 and profile.gender == Gender.FEMALE:
        warnings.append("目标热量低于 1200 大卡/天，可能低于健康底线，请谨慎参考。")
    elif target_calories < 1500 and profile.gender == Gender.MALE:
        warnings.append("目标热量低于 1500 大卡/天，可能低于健康底线，请谨慎参考。")

    macros = calculate_macros(target_calories, profile.goal)
    micros = calculate_micronutrients(profile.gender, profile.special_condition, profile.age)

    return CalculationResult(
        bmr=round(bmr, 1),
        tdee=round(tdee, 1),
        target_calories=round(target_calories, 1),
        macronutrients=macros,
        micronutrients=micros,
        warnings=warnings,
    )
