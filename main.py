import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.models import (
    Profile, ProfileCreate, ProfileUpdate,
    FlagType,
)
from app import profile as profile_service
from app import calc as calc_service
from app import flag as flag_service
from app import meal as meal_service
from app import intake as intake_service
from app.ingredients import get_all_ingredients, Ingredient


app = FastAPI(title="营养师后端服务", version="1.0.0")


@app.get("/", tags=["健康检查"])
def root():
    return {
        "service": "营养师后端服务",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/profiles", response_model=Profile, tags=["用户档案"])
def create_profile(data: ProfileCreate):
    return profile_service.create_profile(data)


@app.get("/profiles", response_model=List[Profile], tags=["用户档案"])
def list_profiles():
    return profile_service.list_profiles()


@app.get("/profiles/{profile_id}", response_model=Profile, tags=["用户档案"])
def get_profile(profile_id: str):
    profile = profile_service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="用户档案不存在")
    return profile


@app.put("/profiles/{profile_id}", response_model=Profile, tags=["用户档案"])
def update_profile(profile_id: str, data: ProfileUpdate):
    profile = profile_service.update_profile(profile_id, data)
    if not profile:
        raise HTTPException(status_code=404, detail="用户档案不存在")
    return profile


@app.delete("/profiles/{profile_id}", tags=["用户档案"])
def delete_profile(profile_id: str):
    success = profile_service.delete_profile(profile_id)
    if not success:
        raise HTTPException(status_code=404, detail="用户档案不存在")
    return {"message": "删除成功"}


@app.get("/profiles/{profile_id}/calculate", tags=["营养计算"])
def calculate_nutrition(profile_id: str):
    profile = profile_service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="用户档案不存在")
    try:
        result = calc_service.calculate_nutrition(profile)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/profiles/{profile_id}/meal-plans", tags=["餐食推荐"])
def get_meal_plans(profile_id: str):
    profile = profile_service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="用户档案不存在")
    try:
        calc_result = calc_service.calculate_nutrition(profile)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    plans = meal_service.generate_meal_plans(
        calc_result=calc_result,
        user_flags=profile.flags,
        num_plans=4,
    )
    return {
        "profile_id": profile_id,
        "target_calories": calc_result.target_calories,
        "warnings": calc_result.warnings,
        "meal_plans": plans,
    }


@app.get("/profiles/{profile_id}/weekly-menu", tags=["餐食推荐"])
def get_weekly_menu(profile_id: str, start_date: Optional[str] = None):
    profile = profile_service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="用户档案不存在")
    try:
        calc_result = calc_service.calculate_nutrition(profile)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")
    else:
        start = date.today()

    weekly_menu: Dict[str, dict] = {}
    for i in range(7):
        day = start + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        seed = i + int(start.strftime("%Y%m%d"))

        plans = meal_service.generate_meal_plans(
            calc_result=calc_result,
            user_flags=profile.flags,
            num_plans=3,
            base_seed=seed,
        )
        weekly_menu[day_str] = {
            "date": day_str,
            "target_calories": calc_result.target_calories,
            "meal_plans": plans,
        }

    return {
        "profile_id": profile_id,
        "start_date": start.strftime("%Y-%m-%d"),
        "warnings": calc_result.warnings,
        "weekly_menu": weekly_menu,
    }


@app.get("/flags", tags=["禁忌标记"])
def list_flags():
    return flag_service.list_all_flags()


@app.get("/ingredients", tags=["食材库"])
def list_ingredients():
    ingredients = get_all_ingredients()
    return [
        {
            "id": ing.id,
            "name": ing.name,
            "category": ing.category,
            "calories_per_100g": ing.calories_per_100g,
            "protein_per_100g": ing.protein_per_100g,
            "carbs_per_100g": ing.carbs_per_100g,
            "fat_per_100g": ing.fat_per_100g,
            "flags": [f.value for f in ing.flags],
        }
        for ing in ingredients
    ]


class IntakeEntryCreate(BaseModel):
    ingredient_id: str
    grams: float


class IntakeCreate(BaseModel):
    entries: List[IntakeEntryCreate]
    date: Optional[str] = None


@app.post("/profiles/{profile_id}/intake", tags=["摄入记录"])
def add_daily_intake(profile_id: str, data: IntakeCreate):
    profile = profile_service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="用户档案不存在")

    intake_date = data.date if data.date else date.today().strftime("%Y-%m-%d")

    from app.intake import IntakeEntry
    entries = [IntakeEntry(ingredient_id=e.ingredient_id, grams=e.grams) for e in data.entries]

    daily = intake_service.add_intake(profile_id, intake_date, entries)
    return daily


@app.get("/profiles/{profile_id}/intake", tags=["摄入记录"])
def get_daily_intake(profile_id: str, date: Optional[str] = None):
    profile = profile_service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="用户档案不存在")

    intake_date = date if date else datetime.now().strftime("%Y-%m-%d")
    daily = intake_service.get_intake(profile_id, intake_date)

    if not daily:
        return {
            "profile_id": profile_id,
            "date": intake_date,
            "entries": [],
            "total_calories": 0,
            "total_protein": 0,
            "total_carbs": 0,
            "total_fat": 0,
            "message": "当日暂无摄入记录",
        }
    return daily


@app.get("/profiles/{profile_id}/deviation", tags=["偏差分析"])
def get_deviation_analysis(profile_id: str, date: Optional[str] = None):
    profile = profile_service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="用户档案不存在")

    try:
        calc_result = calc_service.calculate_nutrition(profile)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    intake_date = date if date else datetime.now().strftime("%Y-%m-%d")
    daily = intake_service.get_intake(profile_id, intake_date)

    if not daily:
        return {
            "profile_id": profile_id,
            "date": intake_date,
            "message": "当日暂无摄入记录，无法进行偏差分析",
            "deviations": [],
            "has_high_deviation": False,
        }

    analysis = intake_service.analyze_deviation(
        recommended_calories=calc_result.target_calories,
        recommended_protein=calc_result.macronutrients.protein,
        recommended_carbs=calc_result.macronutrients.carbs,
        recommended_fat=calc_result.macronutrients.fat,
        actual_intake=daily,
    )
    return {
        "profile_id": profile_id,
        "date": intake_date,
        "analysis": analysis,
    }


@app.get("/profiles/{profile_id}/weekly-deviation", tags=["偏差分析"])
def get_weekly_deviation(profile_id: str, start_date: Optional[str] = None):
    profile = profile_service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="用户档案不存在")

    try:
        calc_result = calc_service.calculate_nutrition(profile)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")
    else:
        from datetime import timedelta
        start = date.today() - timedelta(days=6)

    end = start + timedelta(days=6)
    intakes = intake_service.get_intake_range(profile_id, start, end)

    results = {}
    from datetime import timedelta as td
    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        daily = next((d for d in intakes if d.date == date_str), None)
        if daily:
            analysis = intake_service.analyze_deviation(
                recommended_calories=calc_result.target_calories,
                recommended_protein=calc_result.macronutrients.protein,
                recommended_carbs=calc_result.macronutrients.carbs,
                recommended_fat=calc_result.macronutrients.fat,
                actual_intake=daily,
            )
            results[date_str] = analysis
        else:
            results[date_str] = {
                "date": date_str,
                "message": "当日无摄入记录",
                "deviations": [],
                "has_high_deviation": False,
            }
        current += td(days=1)

    return {
        "profile_id": profile_id,
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
        "weekly_deviations": results,
    }


def main():
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
