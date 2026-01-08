import pandas as pd
import numpy as np

# 1. 실제 SMP 데이터 로드
file_path = r"C:\Users\dltjr\PycharmProjects\PythonProject2\smp_land_2026-01-08.csv"
try:
    df_smp = pd.read_csv(file_path)
    print("✅ SMP 데이터를 성공적으로 불러왔습니다.")
except Exception as e:
    print(f"❌ 파일 로드 실패: {e}")

# 2. e-DRT 표준 차량(아이오닉 5) 및 운영 상수 설정
# 아이오닉 5 Long Range 모델 기준
BATTERY_CAP = 77.4        # 배터리 용량 (kWh)
V2G_AMOUNT = 20.0         # 1일 V2G 방전량 (배터리 수명을 고려하여 약 25%인 20kWh만 사용)
EFFICIENCY = 0.9          # 충/방전 효율 (Round-trip 효율)
C_DEG = 60                # 배터리 열화 비용 (원/kWh, 업계 표준 근사치)

# 3. 데이터 확인 (1시~24시를 0시~23시 인덱스로 매칭하기 위해 확인)
print("\n--- [데이터 상위 5행] ---")
print(df_smp.head())

# 만약 데이터의 'time'이 1~24라면, 계산 편의를 위해 0~23으로 변환해두는 것이 좋습니다.
# df_smp['time'] = df_smp['time'] - 1


# 1. 데이터 정제: 필요한 컬럼만 선택하고 빈 값(NaN)이 있는 행 제거
df_smp_clean = df_smp[['time', 'price']].dropna().copy()

# 2. 'time' 컬럼에서 'h' 제거 및 숫자 변환 (에러 방지를 위해 공백 제거 추가)
df_smp_clean['time'] = df_smp_clean['time'].astype(str).str.replace('h', '').str.strip()
df_smp_clean['hour'] = df_smp_clean['time'].astype(int)

# 3. 충전 시나리오 (새벽 1시~6시) SMP 추출
# 이 시간대 중 가장 저렴할 때 충전한다고 가정 (최소값)
charge_window = df_smp_clean[df_smp_clean['hour'].isin([1, 2, 3, 4, 5, 6])]
smp_low = charge_window['price'].min()
smp_low_hour = charge_window.loc[charge_window['price'].idxmin(), 'hour']

# 4. 방전 시나리오 (오후 14시~17시) SMP 추출
# 이 시간대 중 가장 비쌀 때 전력을 판매한다고 가정 (최대값)
discharge_window = df_smp_clean[df_smp_clean['hour'].isin([14, 15, 16, 17])]
smp_high = discharge_window['price'].max()
smp_high_hour = discharge_window.loc[discharge_window['price'].idxmax(), 'hour']

print(f"--- [Step 2] 데이터 정제 및 SMP 추출 완료 ---")
print(f"📍 최적 충전 시간: {smp_low_hour}시 (가격: {smp_low:.2f}원/kWh)")
print(f"📍 최적 방전 시간: {smp_high_hour}시 (가격: {smp_high:.2f}원/kWh)")

# 1. 일일 수익 계산 로직
# 방전 매출 = 방전량 * 높은 SMP
revenue = V2G_AMOUNT * smp_high

# 충전 비용 = (방전량 / 효율) * 낮은 SMP  (효율 때문에 더 많이 충전해야 함)
charge_cost = (V2G_AMOUNT / EFFICIENCY) * smp_low

# 배터리 열화 비용 = 방전량 * 열화 비용 상수
degradation_cost = V2G_AMOUNT * C_DEG

# 일일 순수익 (Daily Net Profit)
daily_profit = revenue - charge_cost - degradation_cost

# 2. 결과 확장 (차량 12대, 1년 365일 기준)
num_vehicles = 12
annual_profit_per_car = daily_profit * 365
total_annual_profit = annual_profit_per_car * num_vehicles

print(f"--- [Step 3] V2G 경제성 분석 결과 ---")
print(f"💰 차량 1대당 일일 순수익: {daily_profit:,.2f} 원")
print(f"💰 차량 1대당 연간 예상 수익: {annual_profit_per_car/10000:,.1f} 만원")
print(f"🚀 e-DRT 전체(12대) 연간 운영비 절감액: {total_annual_profit/10000:,.1f} 만원")

# 수익성이 마이너스라면? (원주님을 위한 분석 팁)
if daily_profit < 0:
    print("\n💡 분석: 현재 SMP 차이보다 배터리 열화 비용이 커서 수익이 마이너스입니다.")
    print("   이 경우 '열화 비용(C_DEG)'을 낮추거나, 전력 피크 시간대의 보조금 등을 고려해야 합니다.")


# [전략 제안] 보조금 및 기술 발전을 반영한 신규 시나리오
V2G_INCENTIVE = 100  # kWh당 100원의 정책 인센티브 가정
C_DEG_FUTURE = 20    # 기술 발전으로 낮아진 열화 비용

# 신규 일일 순수익 계산
# 순수익 = (방전매출 + 인센티브) - 충전비용 - 신규열화비용
proposed_daily_profit = (V2G_AMOUNT * (smp_high + V2G_INCENTIVE)) - charge_cost - (V2G_AMOUNT * C_DEG_FUTURE)

# 연간 수익 확장
proposed_annual_profit_total = proposed_daily_profit * 365 * 12

print(f"--- [Step 4] 전략 제안: 정책 보조금 반영 시나리오 ---")
print(f"💡 가정: 방전 인센티브 {V2G_INCENTIVE}원/kWh 지급 및 배터리 열화 비용 {C_DEG_FUTURE}원 절감")
print(f"💰 제안 모델 일일 순수익: {proposed_daily_profit:,.2f} 원")
print(f"🚀 e-DRT 전체(12대) 연간 예상 수익: {proposed_annual_profit_total/10000:,.1f} 만원")
print(f"✅ 결과: 마이너스였던 운영비가 연간 {proposed_annual_profit_total/10000:,.1f} 만원 '수익'으로 전환됨")