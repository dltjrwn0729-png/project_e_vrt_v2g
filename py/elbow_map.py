import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from scipy.spatial import distance
import folium
import os

# =========================================================
# 0. 경로 설정 (실행 위치 독립)
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # py/
PROJECT_ROOT = os.path.dirname(BASE_DIR)                # 프로젝트 루트

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
VIS_DIR = os.path.join(PROJECT_ROOT, "visualization")

os.makedirs(VIS_DIR, exist_ok=True)

# =========================================================
# 1. 데이터 로드
# =========================================================

file_path = os.path.join(DATA_DIR, "cheonan_all_stops_over_100.csv")

try:
    df_stops = pd.read_csv(file_path, encoding="utf-8-sig")
except FileNotFoundError:
    print(f"파일을 찾을 수 없습니다: {file_path}. 예시 데이터를 생성합니다.")
    df_stops = pd.DataFrame({
        'lat': np.random.uniform(36.7, 36.95, 100),
        'lon': np.random.uniform(127.05, 127.2, 100)
    })

# =========================================================
# 2. KMeans 클러스터링
# =========================================================

n_clusters = 3
kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
df_stops['cluster_id'] = kmeans.fit_predict(df_stops[['lat', 'lon']])
centroids = kmeans.cluster_centers_

# =========================================================
# 3. 인프라 후보지 (고정 좌표)
# =========================================================

infra_candidates = [
    {"name": "천안한양수자인에코시티 충전소", "lat": 36.7563, "lon": 127.1176, "address": "풍세면 풍세산단로 290"},
    {"name": "천안추모공원 충전소", "lat": 36.6852, "lon": 127.0985, "address": "광덕면 밤나무골길 38"},
    {"name": "천안동남경찰서 충전소", "lat": 36.7886, "lon": 127.1514, "address": "청수6로 73"},
    {"name": "천안박물관 충전소", "lat": 36.7892, "lon": 127.1663, "address": "삼룡동 265-30"},
    {"name": "동남구청 충전소", "lat": 36.8063, "lon": 127.1512, "address": "옛시청길 39"},
    {"name": "남서울대학교 충전소", "lat": 36.9105, "lon": 127.1353, "address": "성환읍 대학로 91"},
    {"name": "서북구청 충전소", "lat": 36.8792, "lon": 127.1726, "address": "성거읍 봉주로 75"}
]
df_infra = pd.DataFrame(infra_candidates)

# =========================================================
# 4. 군집별 최적 허브 매칭
# =========================================================

final_hubs = []
for i, center in enumerate(centroids):
    dists = df_infra.apply(
        lambda row: distance.euclidean(center, [row['lat'], row['lon']]),
        axis=1
    )
    closest_idx = dists.idxmin()
    match_hub = df_infra.loc[closest_idx].to_dict()
    match_hub['target_cluster'] = i
    final_hubs.append(match_hub)

df_final_hubs = pd.DataFrame(final_hubs)

# =========================================================
# 5. 결과 CSV 저장 (visualization 폴더)
# =========================================================

hub_mapping = {
    row['target_cluster']: row['name']
    for _, row in df_final_hubs.iterrows()
}

df_stops['assigned_hub'] = df_stops['cluster_id'].map(hub_mapping)

df_stops.to_csv(
    os.path.join(VIS_DIR, "final_analysis_results.csv"),
    index=False,
    encoding="utf-8-sig"
)

df_final_hubs.to_csv(
    os.path.join(VIS_DIR, "final_hubs_list.csv"),
    index=False,
    encoding="utf-8-sig"
)

print("CSV 결과 저장 완료.")

# =========================================================
# 6. 지도 시각화 (캡처용)
# =========================================================

m = folium.Map(
    location=[df_stops['lat'].mean(), df_stops['lon'].mean()],
    zoom_start=11,
    tiles='cartodbpositron'
)

cluster_colors = ['#E6194B', '#3CB44B', '#4363D8']  # 빨강, 초록, 파랑

# A. 정류소 표시
for _, row in df_stops.iterrows():
    folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=5,
        color=cluster_colors[int(row['cluster_id'])],
        fill=True,
        fill_color=cluster_colors[int(row['cluster_id'])],
        fill_opacity=0.7,
        popup=folium.Popup(
            f"정류소<br>담당 허브: {row['assigned_hub']}",
            max_width=200
        )
    ).add_to(m)

# B. 최종 허브 표시
for _, row in df_final_hubs.iterrows():
    folium.Marker(
        location=[row['lat'], row['lon']],
        icon=folium.Icon(color='darkpurple', icon='star', prefix='fa'),
        tooltip=f"★ 최종 허브: {row['name']}",
        popup=f"<b>{row['name']}</b><br>주소: {row['address']}"
    ).add_to(m)

    folium.Circle(
        location=[row['lat'], row['lon']],
        radius=3000,
        color=cluster_colors[int(row['target_cluster'])],
        fill=True,
        fill_opacity=0.1,
        weight=1
    ).add_to(m)

# =========================================================
# 7. 지도 저장
# =========================================================

map_path = os.path.join(VIS_DIR, "cheonan_final_capture_map.html")
m.save(map_path)

print(f"지도 생성 완료: {map_path}")
