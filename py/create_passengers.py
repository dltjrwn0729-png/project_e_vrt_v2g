import pandas as pd
import numpy as np
import os
import requests
import time

# =========================================================
# 1. 프로젝트 경로 자동 설정
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # py/
PROJECT_ROOT = os.path.dirname(BASE_DIR)  # 프로젝트 루트
DATA_DIR = os.path.join(PROJECT_ROOT, "data")  # data/

os.makedirs(DATA_DIR, exist_ok=True)

# 입력 / 출력 파일 경로
base_file_path = os.path.join(DATA_DIR, "hub_and_stop_locations.csv")
output_file_path = os.path.join(DATA_DIR, "passenger_data.csv")


# =========================================================
# 2. 도로 스냅(Snap) 및 데이터 생성 로직
# =========================================================
def snap_to_road(lat, lon):
    """OSRM API를 사용하여 무작위 좌표를 실제 도로 위로 보정"""
    try:
        url = f"http://router.project-osrm.org/nearest/v1/driving/{lon},{lat}"
        r = requests.get(url, timeout=2)
        if r.status_code == 200:
            data = r.json()
            if data['code'] == 'Ok':
                snapped_lon, snapped_lat = data['waypoints'][0]['location']
                return snapped_lat, snapped_lon
    except:
        pass
    return lat, lon


def generate_peak_passenger_data_v2(base_path, output_path, num_passengers=60):
    try:
        if not os.path.exists(base_path):
            print(f"❌ 파일을 찾을 수 없습니다: {base_path}")
            return

        # 기초 데이터 로드
        df_base = pd.read_csv(base_path)
        df_base.columns = df_base.columns.str.strip()
        stop_indices = df_base[df_base['location_type'] == 1].index.tolist()

        # 천안 도심 범위 설정
        lat_min, lat_max = df_base['lat'].min(), df_base['lat'].max()
        lon_min, lon_max = df_base['lon'].min(), df_base['lon'].max()

        # 피크 타임 가중치 설정 (0분~120분 사이 배정)
        time_batches = [0, 30, 60, 90, 120]
        weights = [0.50, 0.30, 0.10, 0.07, 0.03]

        passengers = []
        print(f"🚀 [Road Snapping] 실제 도로망 기반 수요 생성 시작 (총 {num_passengers}명)")

        for i in range(num_passengers):
            request_time = np.random.choice(time_batches, p=weights)

            # 1. 무작위 좌표 생성 후 2. 도로 위로 보정
            raw_lat = np.random.uniform(lat_min, lat_max)
            raw_lon = np.random.uniform(lon_min, lon_max)
            snapped_lat, snapped_lon = snap_to_road(raw_lat, raw_lon)

            # API 과부하 방지용 미세 대기
            time.sleep(0.05)

            passengers.append({
                'passenger_id': f'PASS_{i + 1:03d}',
                'location_type': 2,
                'lat': snapped_lat,
                'lon': snapped_lon,
                'dest_id': np.random.choice(stop_indices),
                'request_time': request_time
            })

            if (i + 1) % 10 == 0:
                print(f"📦 [{i + 1}/{num_passengers}] 좌표 보정 완료...")

        df_passengers = pd.DataFrame(passengers)
        df_passengers = df_passengers.sort_values(by=['request_time', 'passenger_id']).reset_index(drop=True)

        # 저장
        df_passengers.to_csv(output_path, index=False, encoding='utf-8-sig')

        print(f"\n✅ [완료] 도로 기반 고도화 수요 데이터가 생성되었습니다.")
        print(f"📍 위치: {output_path}")
        print(df_passengers['request_time'].value_counts().sort_index().to_string())

    except Exception as e:
        print(f"❌ 에러 발생: {e}")


if __name__ == "__main__":
    # 공모전용 60명 피크타임 데이터 생성
    generate_peak_passenger_data_v2(base_file_path, output_file_path, num_passengers=60)