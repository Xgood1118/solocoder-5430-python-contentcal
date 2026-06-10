import random
from typing import List, Dict
from pydantic import BaseModel

from app.models import FlagType
from app.ingredients import Ingredient, get_all_ingredients
from app.flag import filter_ingredients_by_flags
from app.calc import CalculationResult


class MealItem(BaseModel):
    ingredient_id: str
    ingredient_name: str
    grams: float
    calories: float
    protein: float
    carbs: float
    fat: float


class MealPlan(BaseModel):
    name: str
    meals: Dict[str, List[MealItem]]
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    calorie_deviation_pct: float


def _get_ingredients_by_category(
    ingredients: List[Ingredient],
) -> Dict[str, List[Ingredient]]:
    categories: Dict[str, List[Ingredient]] = {}
    for ing in ingredients:
        if ing.category not in categories:
            categories[ing.category] = []
        categories[ing.category].append(ing)
    return categories


def _calc_item(ingredient: Ingredient, grams: float) -> MealItem:
    factor = grams / 100.0
    return MealItem(
        ingredient_id=ingredient.id,
        ingredient_name=ingredient.name,
        grams=grams,
        calories=round(ingredient.calories_per_100g * factor, 1),
        protein=round(ingredient.protein_per_100g * factor, 1),
        carbs=round(ingredient.carbs_per_100g * factor, 1),
        fat=round(ingredient.fat_per_100g * factor, 1),
    )


def _generate_plan(
    plan_name: str,
    target_calories: float,
    target_protein: float,
    target_carbs: float,
    target_fat: float,
    categories: Dict[str, List[Ingredient]],
    seed: int,
) -> MealPlan:
    rng = random.Random(seed)

    proteins = categories.get("肉类", []) + categories.get("水产", []) + categories.get("豆制品", []) + categories.get("蛋类", [])
    carbs_sources = categories.get("主食", []) + categories.get("豆类", [])
    veggies = categories.get("蔬菜", [])
    fruits = categories.get("水果", [])
    dairy = categories.get("乳制品", [])
    nuts = categories.get("坚果", [])
    oils = categories.get("油脂", [])

    protein_ing = rng.choice(proteins) if proteins else None
    carb_ing = rng.choice(carbs_sources) if carbs_sources else None
    veggie_ings = rng.sample(veggies, min(2, len(veggies))) if veggies else []
    fruit_ing = rng.choice(fruits) if fruits else None

    breakfast: List[MealItem] = []
    lunch: List[MealItem] = []
    dinner: List[MealItem] = []
    snacks: List[MealItem] = []

    if carb_ing:
        breakfast_calories = target_calories * 0.30
        lunch_calories = target_calories * 0.40
        dinner_calories = target_calories * 0.30

        if carb_ing:
            carb_per_100g = carb_ing.calories_per_100g
            breakfast_carb_grams = (breakfast_calories * 0.5) / carb_per_100g * 100
            lunch_carb_grams = (lunch_calories * 0.4) / carb_per_100g * 100
            dinner_carb_grams = (dinner_calories * 0.3) / carb_per_100g * 100
            breakfast.append(_calc_item(carb_ing, round(breakfast_carb_grams, 0)))
            lunch.append(_calc_item(carb_ing, round(lunch_carb_grams, 0)))
            dinner.append(_calc_item(carb_ing, round(dinner_carb_grams, 0)))

        if protein_ing:
            prot_per_100g = protein_ing.calories_per_100g
            lunch_prot_grams = (lunch_calories * 0.35) / prot_per_100g * 100
            dinner_prot_grams = (dinner_calories * 0.4) / prot_per_100g * 100
            lunch.append(_calc_item(protein_ing, round(lunch_prot_grams, 0)))
            dinner.append(_calc_item(protein_ing, round(dinner_prot_grams, 0)))

        for veg in veggie_ings:
            veg_grams = 100.0 + rng.random() * 50
            lunch.append(_calc_item(veg, veg_grams))

        if len(veggie_ings) >= 1:
            dinner.append(_calc_item(veggie_ings[0], 120.0))

        if fruit_ing:
            snacks.append(_calc_item(fruit_ing, 150.0))

        if dairy and rng.random() > 0.3:
            d_ing = rng.choice(dairy)
            breakfast.append(_calc_item(d_ing, 200.0))

        if nuts and rng.random() > 0.5:
            n_ing = rng.choice(nuts)
            snacks.append(_calc_item(n_ing, 15.0))

        if oils:
            oil_ing = rng.choice(oils)
            lunch.append(_calc_item(oil_ing, 8.0))
            dinner.append(_calc_item(oil_ing, 6.0))

    all_items = breakfast + lunch + dinner + snacks
    total_cal = sum(item.calories for item in all_items)
    total_prot = sum(item.protein for item in all_items)
    total_carb = sum(item.carbs for item in all_items)
    total_fat = sum(item.fat for item in all_items)

    if total_cal > 0:
        scale = target_calories / total_cal
        for meal_list in [breakfast, lunch, dinner, snacks]:
            for item in meal_list:
                item.grams = round(item.grams * scale, 0)
                item.calories = round(item.calories * scale, 1)
                item.protein = round(item.protein * scale, 1)
                item.carbs = round(item.carbs * scale, 1)
                item.fat = round(item.fat * scale, 1)

        total_cal = sum(item.calories for item in all_items)
        total_prot = sum(item.protein for item in all_items)
        total_carb = sum(item.carbs for item in all_items)
        total_fat = sum(item.fat for item in all_items)

    deviation = (total_cal - target_calories) / target_calories * 100

    return MealPlan(
        name=plan_name,
        meals={
            "早餐": breakfast,
            "午餐": lunch,
            "晚餐": dinner,
            "加餐": snacks,
        },
        total_calories=round(total_cal, 1),
        total_protein=round(total_prot, 1),
        total_carbs=round(total_carb, 1),
        total_fat=round(total_fat, 1),
        calorie_deviation_pct=round(deviation, 2),
    )


def generate_meal_plans(
    calc_result: CalculationResult,
    user_flags: List[FlagType] | None = None,
    num_plans: int = 4,
    base_seed: int = 0,
) -> List[MealPlan]:
    if user_flags is None:
        user_flags = []

    all_ingredients = get_all_ingredients()
    filtered = filter_ingredients_by_flags(all_ingredients, user_flags, combine_mode="and")

    if not filtered:
        return []

    categories = _get_ingredients_by_category(filtered)

    plans: List[MealPlan] = []
    for i in range(num_plans):
        plan = _generate_plan(
            plan_name=f"方案{i + 1}",
            target_calories=calc_result.target_calories,
            target_protein=calc_result.macronutrients.protein,
            target_carbs=calc_result.macronutrients.carbs,
            target_fat=calc_result.macronutrients.fat,
            categories=categories,
            seed=base_seed * 100 + i + 1,
        )
        if abs(plan.calorie_deviation_pct) <= 5.0:
            plans.append(plan)

    if not plans:
        plans.append(_generate_plan(
            plan_name="方案1",
            target_calories=calc_result.target_calories,
            target_protein=calc_result.macronutrients.protein,
            target_carbs=calc_result.macronutrients.carbs,
            target_fat=calc_result.macronutrients.fat,
            categories=categories,
            seed=base_seed * 100 + 42,
        ))

    return plans[:5]
