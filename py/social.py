import pandas as pd

# ==========================================================
# [중요] 이전 단계(경제성 분석)에서 도출된 결과값들입니다.
# 에러 방지를 위해 고정 수치(Constants)로 정의합니다.
# ==========================================================
DAILY_PROFIT = -866.6              # 차량 1대당 일일 순수익 (현행)
PROPOSED_ANNUAL_PROFIT_TOTAL = 11300000  # 전체 차량 연간 순수익 (전략 제안)

# 1. 운영 규모 설정
NUM_VEHICLES = 12           # 운영 차량 대수
ANNUAL_DAYS = 365           # 연간 운영 일수
DAILY_AVG_DIST = 200        # 차량 1대당 일일 평균 주행거리 (km)
                            # (보통 도심형 DRT의 평균 주행거리를 150~250km로 잡습니다)

# 2. 탄소 배출 계수 설정 (단위: kg/km)
CO2_BUS_FACTOR = 0.250      # 기존 버스 (250g)
CO2_EDRT_FACTOR = 0.100     # 전기 DRT (100g)

# 3. 연간 총 주행거리 계산
total_annual_dist = NUM_VEHICLES * DAILY_AVG_DIST * ANNUAL_DAYS

print(f"--- [Step 1] 사회적 가치 분석 데이터 설정 완료 ---")
print(f"📍 e-DRT 시스템 총 차량 대수: {NUM_VEHICLES} 대")
print(f"📍 전체 차량 연간 총 주행거리: {total_annual_dist:,.0f} km")

# 1. 연간 탄소 저감량 계산 (kg)
annual_co2_reduction_kg = (CO2_BUS_FACTOR - CO2_EDRT_FACTOR) * total_annual_dist
annual_co2_reduction_ton = annual_co2_reduction_kg / 1000

# 2. 소나무 식재 효과 환산 (그루)
# 소나무 1그루당 연간 CO2 흡수량 = 6.6kg (산림청 기준)
PINE_TREE_ABSORPTION = 6.6
pine_tree_count = annual_co2_reduction_kg / PINE_TREE_ABSORPTION

print(f"--- [Step 2] 탄소 저감 및 환경 가치 산출 완료 ---")
print(f"🌍 연간 탄소 배출 저감량: {annual_co2_reduction_ton:,.1f} 톤 (ton)")
print(f"🌲 소나무 식재 효과: 연간 약 {pine_tree_count:,.0f} 그루")
print(f"\n💡 비유 문구: \"본 e-DRT 시스템 도입은 천안시에 연간 {annual_co2_reduction_ton:,.1f}톤의 탄소를 줄이며,")
print(f"   이는 소나무 {pine_tree_count:,.0f}그루를 심는 것과 동일한 환경적 기여를 합니다.\"")

# 1. 최종 결과 요약 데이터 구성
summary_data = {
    "구분": [
        "운영 규모",
        "연간 총 주행거리",
        "V2G 일일 순수익 (현행)",
        "V2G 연간 순수익 (전략 제안)",
        "연간 탄소(CO2) 저감량",
        "소나무 식재 효과"
    ],
    "수치": [
        f"{NUM_VEHICLES} 대",                    # num_vehicles -> NUM_VEHICLES로 수정
        f"{total_annual_dist:,.0f} km",
        f"{DAILY_PROFIT:,.0f} 원/대",             # daily_profit -> DAILY_PROFIT으로 수정
        f"{PROPOSED_ANNUAL_PROFIT_TOTAL/10000:,.1f} 만원", # proposed_annual_profit_total 변수 연결
        f"{annual_co2_reduction_ton:,.1f} 톤",
        f"약 {pine_tree_count:,.0f} 그루"
    ],
    "비고": [
        "아이오닉 5 기준",
        "일 200km 주행 가정",
        "배터리 열화 비용 반영",
        "정부 인센티브 포함 시",
        "버스 대비 절감량",
        "30년생 소나무 기준"
    ]
}

# 2. 데이터프레임 생성 및 출력
df_final_report = pd.DataFrame(summary_data)

print("\n" + "="*60)
print("       [천안시 스마트 e-DRT 도입 성과 기대효과 요약]       ")
print("="*60)
print(df_final_report.to_string(index=False, justify='center'))
print("="*60)

# 3. 추가 시각화용 텍스트 (발표 스크립트 활용)
print(f"\n📢 [Key Message]")
print(f"\"본 e-DRT 시스템 도입 시, 연간 소나무 {pine_tree_count:,.0f}그루를 심는 환경적 효과와 함께")
print(f" 적정 인센티브 도입 시 연간 약 {PROPOSED_ANNUAL_PROFIT_TOTAL/10000:,.0f}만원의 운영 수익을 창출할 수 있습니다.\"")