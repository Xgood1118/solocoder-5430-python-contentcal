import sys
sys.path.insert(0, '.')

from app.models import ProfileCreate, Gender, ActivityLevel, Goal, FlagType, SpecialCondition
from app import profile as profile_service
from app import calc as calc_service
from app import meal as meal_service
from app import intake as intake_service
from app.intake import IntakeEntry

print("=" * 60)
print("测试 1: 创建用户档案")
print("=" * 60)

profile_data = ProfileCreate(
    name="测试用户",
    gender=Gender.MALE,
    age=30,
    height=175,
    weight=70,
    activity_level=ActivityLevel.MODERATE,
    goal=Goal.FAT_LOSS,
    flags=[],
    special_condition=SpecialCondition.NONE,
)

profile = profile_service.create_profile(profile_data)
print(f"用户ID: {profile.id}")
print(f"姓名: {profile.name}")
print(f"性别: {profile.gender}")
print(f"年龄: {profile.age}")
print(f"身高: {profile.height}cm")
print(f"体重: {profile.weight}kg")
print(f"BMI: {profile.weight / ((profile.height/100)**2):.1f}")
print()

print("=" * 60)
print("测试 2: 营养计算")
print("=" * 60)

result = calc_service.calculate_nutrition(profile)
print(f"BMR: {result.bmr} kcal")
print(f"TDEE: {result.tdee} kcal")
print(f"目标热量: {result.target_calories} kcal")
print()
print("宏量营养素:")
print(f"  蛋白质: {result.macronutrients.protein} g")
print(f"  碳水: {result.macronutrients.carbs} g")
print(f"  脂肪: {result.macronutrients.fat} g")
print()
print("微量元素:")
print(f"  钙: {result.micronutrients.calcium_mg} mg")
print(f"  铁: {result.micronutrients.iron_mg} mg")
print(f"  维生素C: {result.micronutrients.vitamin_c_mg} mg")
print(f"  维生素D: {result.micronutrients.vitamin_d_iu} IU")
print()
if result.warnings:
    print("警告:")
    for w in result.warnings:
        print(f"  - {w}")
print()

print("=" * 60)
print("测试 3: 餐食推荐")
print("=" * 60)

plans = meal_service.generate_meal_plans(result, profile.flags, num_plans=3)
print(f"生成了 {len(plans)} 个餐食方案")
for i, plan in enumerate(plans):
    print(f"\n方案 {i+1}: {plan.name}")
    print(f"  总热量: {plan.total_calories} kcal (偏差: {plan.calorie_deviation_pct}%)")
    print(f"  蛋白质: {plan.total_protein} g")
    print(f"  碳水: {plan.total_carbs} g")
    print(f"  脂肪: {plan.total_fat} g")
    for meal_name, items in plan.meals.items():
        if items:
            print(f"  {meal_name}:")
            for item in items:
                print(f"    - {item.ingredient_name} {item.grams}g ({item.calories} kcal)")
print()

print("=" * 60)
print("测试 4: 年龄边界（超出范围应该报错）")
print("=" * 60)

try:
    old_profile_data = ProfileCreate(
        name="老年人",
        gender=Gender.MALE,
        age=70,
        height=170,
        weight=65,
        activity_level=ActivityLevel.SEDENTARY,
        goal=Goal.MAINTENANCE,
    )
    old_profile = profile_service.create_profile(old_profile_data)
    result = calc_service.calculate_nutrition(old_profile)
    print("错误：应该抛出异常但没有")
except ValueError as e:
    print(f"正确抛出异常: {e}")
print()

print("=" * 60)
print("测试 5: 极端 BMI 警告")
print("=" * 60)

bmi_profile_data = ProfileCreate(
    name="很瘦的人",
    gender=Gender.FEMALE,
    age=25,
    height=165,
    weight=40,
    activity_level=ActivityLevel.LIGHT,
    goal=Goal.MAINTENANCE,
)
bmi_profile = profile_service.create_profile(bmi_profile_data)
bmi_result = calc_service.calculate_nutrition(bmi_profile)
print(f"BMI: {bmi_profile.weight / ((bmi_profile.height/100)**2):.1f}")
print(f"警告数量: {len(bmi_result.warnings)}")
for w in bmi_result.warnings:
    print(f"  - {w}")
print()

print("=" * 60)
print("测试 6: 禁忌过滤（素食 + 无麸质）")
print("=" * 60)

veg_profile_data = ProfileCreate(
    name="素食者",
    gender=Gender.FEMALE,
    age=28,
    height=165,
    weight=55,
    activity_level=ActivityLevel.MODERATE,
    goal=Goal.MAINTENANCE,
    flags=[FlagType.VEGETARIAN, FlagType.ALLERGY_GLUTEN],
)
veg_profile = profile_service.create_profile(veg_profile_data)
veg_result = calc_service.calculate_nutrition(veg_profile)
veg_plans = meal_service.generate_meal_plans(veg_result, veg_profile.flags, num_plans=2)
print(f"生成了 {len(veg_plans)} 个素食+无麸质方案")
if veg_plans:
    plan = veg_plans[0]
    print(f"方案热量: {plan.total_calories} kcal (偏差: {plan.calorie_deviation_pct}%)")
    all_ingredients = []
    for items in plan.meals.values():
        all_ingredients.extend([i.ingredient_name for i in items])
    print(f"食材: {', '.join(all_ingredients)}")
print()

print("=" * 60)
print("测试 7: 摄入记录和偏差分析")
print("=" * 60)

entries = [
    IntakeEntry(ingredient_id="rice", grams=150),
    IntakeEntry(ingredient_id="chicken_breast", grams=200),
    IntakeEntry(ingredient_id="broccoli", grams=100),
    IntakeEntry(ingredient_id="egg", grams=50),
]

daily = intake_service.add_intake(profile.id, "2024-01-15", entries)
print(f"摄入日期: {daily.date}")
print(f"总热量: {daily.total_calories} kcal")
print(f"蛋白质: {daily.total_protein} g")
print(f"碳水: {daily.total_carbs} g")
print(f"脂肪: {daily.total_fat} g")

analysis = intake_service.analyze_deviation(
    recommended_calories=result.target_calories,
    recommended_protein=result.macronutrients.protein,
    recommended_carbs=result.macronutrients.carbs,
    recommended_fat=result.macronutrients.fat,
    actual_intake=daily,
)
print()
print("偏差分析:")
for dev in analysis.deviations:
    flag = " ⚠️ 高亮" if dev.is_highlighted else ""
    print(f"  {dev.nutrient}: 推荐 {dev.recommended}, 实际 {dev.actual}, 偏差 {dev.deviation_pct}%{flag}")
print(f"有高偏差项: {analysis.has_high_deviation}")
print()

print("=" * 60)
print("测试 8: 体重历史记录")
print("=" * 60)

from app.models import ProfileUpdate
update_data = ProfileUpdate(weight=68)
updated = profile_service.update_profile(profile.id, update_data)
print(f"更新后体重: {updated.weight} kg")
print(f"体重历史记录数: {len(updated.weight_history)}")
for record in updated.weight_history:
    print(f"  {record.timestamp}: {record.weight} kg")
print()

print("=" * 60)
print("✅ 所有测试完成！")
print("=" * 60)
