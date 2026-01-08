import geopandas as gpd
import pandas as pd
import folium
from folium import plugins
import warnings
from sklearn.cluster import DBSCAN
import numpy as np
import os

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # py/
PROJECT_ROOT = os.path.dirname(BASE_DIR)                # 프로젝트 루트

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
VIS_DIR = os.path.join(PROJECT_ROOT, "visualization")

os.makedirs(VIS_DIR, exist_ok=True)

bus_excel_path = os.path.join(DATA_DIR,"국토교통부_전국 버스정류장 위치정보_20251031.xlsx")

grid_shp_path = os.path.join(DATA_DIR,"grid_data",
"(B100)국토통계_인구정보-총 인구 수(전체)-(격자) 100M_충청남도 천안시_202410","nlsp_021001001.shp")

INSTALL_THRESHOLD = 100
SERVICE_DIST = 400

# 파일 존재 여부 최종 확인
if not os.path.exists(grid_shp_path):
    print(f"경로 에러: {grid_shp_path}\n파일을 찾을 수 없습니다. 경로를 다시 확인해주세요.")
    exit()

# =========================================================
# 2. 데이터 로드 및 전처리
# =========================================================

print("1/4: 데이터를 로드하고 천안시 구역을 추출 중입니다...")
grid = gpd.read_file(grid_shp_path).to_crs(epsg=5179)
cheonan_boundary_gdf = gpd.GeoDataFrame(geometry=[grid.union_all()], crs="EPSG:5179")

bus_df = pd.read_excel(bus_excel_path)
bus_gdf = gpd.GeoDataFrame(
    bus_df, geometry=gpd.points_from_xy(bus_df['경도'], bus_df['위도']), crs="EPSG:4326"
).to_crs(epsg=5179)
bus_stops = bus_gdf[bus_gdf.geometry.intersects(cheonan_boundary_gdf.geometry[0])].copy()

# =========================================================
# 3. 사각지대 히트맵 분석 및 입지 선정
# =========================================================

print("2/4: 교통 사각지대 내 인구 밀집도를 분석 중입니다...")
service_area_poly = bus_stops.buffer(SERVICE_DIST).union_all()
shadow_grids = grid[(grid['val'] > 0) & (~grid.geometry.centroid.within(service_area_poly))].copy()

# 히트맵용 가중치 데이터 변환
shadow_grids_4326 = shadow_grids.to_crs(epsg=4326)
heatmap_data = []
for _, row in shadow_grids_4326.iterrows():
    # [위도, 경도, 가중치(인구수)]
    heatmap_data.append([row.geometry.centroid.y, row.geometry.centroid.x, row['val']])

# DBSCAN 기반 신규 거점 추출
coords = np.array(list(zip(shadow_grids.geometry.centroid.x, shadow_grids.geometry.centroid.y)))
dbscan = DBSCAN(eps=SERVICE_DIST, min_samples=1)
clusters = dbscan.fit_predict(coords)

master_points = pd.DataFrame({
    'lat': shadow_grids_4326.geometry.centroid.y,
    'lon': shadow_grids_4326.geometry.centroid.x,
    'weight': shadow_grids['val'],
    'cluster': clusters
})

final_hubs = []
for label in set(clusters):
    if label == -1: continue
    cluster_data = master_points[master_points['cluster'] == label]
    if cluster_data['weight'].sum() >= INSTALL_THRESHOLD:
        best_row = cluster_data.loc[cluster_data['weight'].idxmax()]
        final_hubs.append({'lat': best_row['lat'], 'lon': best_row['lon'], 'pop': cluster_data['weight'].sum()})
hubs_df = pd.DataFrame(final_hubs)

# =========================================================
# 4. 보고서 전용 시각화 (이미지 스타일 히트맵)
# =========================================================

print("3/4: 시각화 결과물을 생성 중입니다...")
m = folium.Map(location=[36.815, 127.113], zoom_start=12, tiles='cartodbpositron')

# (1) 천안시 행정 구역 경계 (굵은 검정색 테두리)

folium.GeoJson(
    cheonan_boundary_gdf.to_crs(epsg=4326),
    style_function=lambda x: {'color': '#000000', 'weight': 3.5, 'fillOpacity': 0},
    name="천안시 경계"
).add_to(m)

# (2) 기존 정류장 영역 (테두리 제거, 배경 회색 그림자)

for _, row in bus_stops.to_crs(epsg=4326).iterrows():
    folium.Circle(
        [row.geometry.y, row.geometry.x], radius=SERVICE_DIST,
        color='none', fill=True, fill_color='#95a5a6', fill_opacity=0.15
    ).add_to(m)

# (3) 인구 밀도 히트맵 (파랑-초록-노랑-빨강 그라데이션)

plugins.HeatMap(
    heatmap_data,
    radius=18,
    blur=20,
    min_opacity=0.4,
    gradient={0.2: 'blue', 0.4: 'lime', 0.6: 'yellow', 1.0: 'red'},
    name="사각지대 인구 밀도"
).add_to(m)

# (4) 신규 e-DRT 정류장 (영역 없이 버스 아이콘 마커만)

for i, row in hubs_df.iterrows():
    popup_txt = f"<b>신규 정류장 {i+1}</b><br>커버 인구: {int(row['pop'])}명"
    folium.Marker(
        [row['lat'], row['lon']],
        tooltip=f"제안 거점 {i+1}",
        popup=folium.Popup(popup_txt, max_width=200),
        icon=folium.Icon(color='darkred', icon='bus', prefix='fa')
    ).add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

output_path = os.path.join(VIS_DIR, "cheonan_heatmap.html")
m.save(output_path)

print("4/4: 모든 작업이 완료되었습니다!")