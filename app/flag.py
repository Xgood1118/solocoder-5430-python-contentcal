from typing import Dict, List, Set
from app.models import FlagType


FLAG_LABELS: Dict[FlagType, str] = {
    FlagType.ALLERGY_PEANUT: "花生过敏",
    FlagType.ALLERGY_GLUTEN: "麸质过敏",
    FlagType.ALLERGY_LACTOSE: "乳糖不耐受",
    FlagType.ALLERGY_SEAFOOD: "海鲜过敏",
    FlagType.VEGETARIAN: "素食",
    FlagType.VEGAN: "纯素",
    FlagType.HALAL: "清真",
    FlagType.KOSHER: "犹太洁食",
}


FLAG_CATEGORIES: Dict[str, List[FlagType]] = {
    "过敏原": [
        FlagType.ALLERGY_PEANUT,
        FlagType.ALLERGY_GLUTEN,
        FlagType.ALLERGY_LACTOSE,
        FlagType.ALLERGY_SEAFOOD,
    ],
    "宗教/饮食禁忌": [
        FlagType.VEGETARIAN,
        FlagType.VEGAN,
        FlagType.HALAL,
        FlagType.KOSHER,
    ],
}


EXCLUSION_FLAGS: Set[FlagType] = {
    FlagType.ALLERGY_PEANUT,
    FlagType.ALLERGY_GLUTEN,
    FlagType.ALLERGY_LACTOSE,
    FlagType.ALLERGY_SEAFOOD,
}


INCLUSION_FLAGS: Set[FlagType] = {
    FlagType.VEGETARIAN,
    FlagType.VEGAN,
    FlagType.HALAL,
    FlagType.KOSHER,
}


def get_flag_label(flag: FlagType) -> str:
    return FLAG_LABELS.get(flag, flag.value)


def list_all_flags() -> Dict[str, List[Dict[str, str]]]:
    result: Dict[str, List[Dict[str, str]]] = {}
    for category, flags in FLAG_CATEGORIES.items():
        result[category] = [
            {"value": f.value, "label": get_flag_label(f)} for f in flags
        ]
    return result


def _split_flags(user_flags: List[FlagType]) -> tuple[Set[FlagType], Set[FlagType]]:
    exclusion = set()
    inclusion = set()
    for f in user_flags:
        if f in EXCLUSION_FLAGS:
            exclusion.add(f)
        elif f in INCLUSION_FLAGS:
            inclusion.add(f)
    return exclusion, inclusion


def check_flags_compatible(
    ingredient_flags: Set[FlagType],
    user_flags: List[FlagType],
    combine_mode: str = "and",
) -> bool:
    if not user_flags:
        return True

    user_exclusion, user_inclusion = _split_flags(user_flags)

    if user_exclusion:
        if combine_mode == "and":
            if user_exclusion & ingredient_flags:
                return False
        else:
            if len(user_exclusion & ingredient_flags) == len(user_exclusion):
                return False

    if user_inclusion:
        if combine_mode == "and":
            if not user_inclusion.issubset(ingredient_flags):
                return False
        else:
            if not (user_inclusion & ingredient_flags):
                return False

    return True


def filter_ingredients_by_flags(
    ingredients: list,
    user_flags: List[FlagType],
    combine_mode: str = "and",
) -> list:
    if not user_flags:
        return ingredients

    filtered = []
    for ing in ingredients:
        if check_flags_compatible(ing.flags, user_flags, combine_mode):
            filtered.append(ing)
    return filtered
