import geopandas as gpd
import pandas as pd
import folium
from sklearn.cluster import DBSCAN
import numpy as np
import os
import warnings

warnings.filterwarnings("ignore")

# =========================================================
# 0. 프로젝트 기준 경로 설정
# =========================================================
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
VIS_DIR = os.path.join(BASE_DIR, "visualization")

os.makedirs(VIS_DIR, exist_ok=True)

# =========================================================
# 1. 설정 및 경로
# =========================================================
BUS_EXCEL_PATH = os.path.join(
    DATA_DIR,
    "국토교통부_전국 버스정류장 위치정보_20251031.xlsx"
)

GRID_SHP_PATH = os.path.join(
    DATA_DIR,
    "grid_data",
    "(B100)국토통계_인구정보-총 인구 수(전체)-(격자) 100M_충청남도 천안시_202410",
    "nlsp_021001001.shp"
)

INSTALL_THRESHOLD = 100   # ✅ 100명 이상
SERVICE_DIST = 400        # 서비스 반경 400m

# =========================================================
# 2. 데이터 로드 및 사각지대 분석
# =========================================================
print("1/4: 데이터 로드 중...")

grid = gpd.read_file(GRID_SHP_PATH).to_crs(epsg=5179)

bus_df = pd.read_excel(BUS_EXCEL_PATH)
bus_gdf = gpd.GeoDataFrame(
    bus_df,
    geometry=gpd.points_from_xy(bus_df['경도'], bus_df['위도']),
    crs="EPSG:4326"
).to_crs(epsg=5179)

# 천안시 경계 생성
cheonan_boundary = grid.geometry.union_all().convex_hull

# 천안시 내부 정류장만 필터링
bus_stops = bus_gdf[bus_gdf.geometry.intersects(cheonan_boundary)].copy()

print(f" - 천안시 버스정류장 수: {len(bus_stops)}")

# 기존 정류장 서비스권 (400m)
service_area = bus_stops.buffer(SERVICE_DIST).union_all()

# 사각지대 격자 추출 (인구 > 0)
shadow_grids = grid[
    (grid['val'] > 0) &
    (~grid.geometry.centroid.within(service_area))
].copy()

print(f" - 사각지대 격자 수: {len(shadow_grids)}")

# =========================================================
# 3. DBSCAN 기반 밀집지역 전수 추출
# =========================================================
print("2/4: DBSCAN 클러스터링 중...")

coords = np.array([
    (pt.x, pt.y) for pt in shadow_grids.geometry.centroid
])

dbscan = DBSCAN(eps=SERVICE_DIST, min_samples=1)
clusters = dbscan.fit_predict(coords)

shadow_grids['cluster'] = clusters

# 위경도 변환
shadow_grids_ll = shadow_grids.to_crs(epsg=4326)
shadow_grids['lat'] = shadow_grids_ll.geometry.centroid.y
shadow_grids['lon'] = shadow_grids_ll.geometry.centroid.x

# =========================================================
# 4. 100명 이상 클러스터만 후보지로 선정
# =========================================================
candidates = []

for label in sorted(shadow_grids['cluster'].unique()):
    cluster_df = shadow_grids[shadow_grids['cluster'] == label]
    total_pop = cluster_df['val'].sum()

    if total_pop >= INSTALL_THRESHOLD:
        best_row = cluster_df.loc[cluster_df['val'].idxmax()]

        candidates.append({
            "lat": best_row['lat'],
            "lon": best_row['lon'],
            "total_pop": int(total_pop),
            "grid_count": len(cluster_df)
        })

candidates_df = pd.DataFrame(candidates)
candidates_df = candidates_df.sort_values("total_pop", ascending=False).reset_index(drop=True)
candidates_df['node_id'] = candidates_df.index + 1

print(f"3/4: 후보지 {len(candidates_df)}곳 선정 완료")

# =========================================================
# 5. 시각화 및 결과 저장
# =========================================================
print("4/4: 지도 생성 및 저장 중...")

m = folium.Map(
    location=[candidates_df['lat'].mean(), candidates_df['lon'].mean()],
    zoom_start=11,
    tiles="cartodbpositron"
)

for _, row in candidates_df.iterrows():
    folium.Marker(
        [row['lat'], row['lon']],
        tooltip=f"후보 {row['node_id']} ({row['total_pop']}명)",
        popup=(
            f"<b>후보지 {row['node_id']}</b><br>"
            f"총 인구: {row['total_pop']}명<br>"
            f"격자 수: {row['grid_count']}"
        ),
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(m)

csv_path = os.path.join(VIS_DIR, "cheonan_all_stops_over_100.csv")
map_path = os.path.join(VIS_DIR, "cheonan_all_stops_over_100_map.html")

candidates_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
m.save(map_path)

print("=" * 60)
print("✅ 분석 완료")
print(f" - 후보지 수: {len(candidates_df)}")
print(f" - CSV 저장: {csv_path}")
print(f" - 지도 저장: {map_path}")
print("=" * 60)
print("👉 다음 단계: 허브 후보 선별 / 기존 노선과 병합 가능")
