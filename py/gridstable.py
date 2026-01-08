# 1. 전력망 기여도 관련 상수 설정
DISCHARGE_POWER_PER_CAR = 10  # 대당 방전 출력 (10kW)
NUM_VEHICLES_CURRENT = 12     # 현재 프로젝트 규모
NUM_VEHICLES_EXPANDED = 50    # 향후 확대 시나리오 (사용자 제안치)

# 아파트 1세대당 피크 시간대 평균 사용량 (약 3.33kW 가정)
# (500kW / 150세대 = 3.33kW 기준)
POWER_PER_HOUSEHOLD = 3.33

# 2. 피크 쉐이빙 용량 계산
current_shaving_kw = DISCHARGE_POWER_PER_CAR * NUM_VEHICLES_CURRENT
expanded_shaving_kw = DISCHARGE_POWER_PER_CAR * NUM_VEHICLES_EXPANDED

# 3. 수혜 가구 수 환산
households_current = current_shaving_kw / POWER_PER_HOUSEHOLD
households_expanded = expanded_shaving_kw / POWER_PER_HOUSEHOLD

print(f"--- [Step 3-2] 전력망 안정성(Peak Shaving) 분석 완료 ---")
print(f"📍 [현재] e-DRT 12대 동시 방전 시: {current_shaving_kw} kW 공급")
print(f"   ㄴ 효과: 피크 시간대 아파트 약 {households_current:.0f}세대 전력 커버")

print(f"\n📍 [확대] e-DRT 50대 동시 방전 시: {expanded_shaving_kw} kW 공급")
print(f"   ㄴ 효과: 피크 시간대 아파트 약 {households_expanded:.0f}세대 전력 커버")

print(f"\n💡 [비유 문구]")
print(f"\"천안시 전력 피크 발생 시, e-DRT {NUM_VEHICLES_EXPANDED}대의 V2G 가동만으로")
print(f" 아파트 {households_expanded:.0f}세대가 동시 사용할 수 있는 {expanded_shaving_kw}kW의 전력을 공급하여")
print(f" 도시 전력망의 과부하를 방지하고 블랙아웃 위험을 낮춥니다.\"")