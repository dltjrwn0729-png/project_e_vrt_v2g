import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import seaborn as sns
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # py/
PROJECT_ROOT = os.path.dirname(BASE_DIR)                # 프로젝트 루트

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
VIS_DIR = os.path.join(PROJECT_ROOT, "visualization")

os.makedirs(VIS_DIR, exist_ok=True)

# ---------------------------------------------------------
# 1. 데이터 불러오기 (인코딩 수정)
# ---------------------------------------------------------

file_path = os.path.join(DATA_DIR, "cheonan_all_stops_over_100.csv")


try:
    df_stops = pd.read_csv(file_path, encoding='utf-8-sig')
except:
    # 만약 위 방법도 안 되면 'cp949'로 시도
    df_stops = pd.read_csv(file_path, encoding='cp949')

# 컬럼명에 혹시 모를 공백 제거 (안전장치)
df_stops.columns = df_stops.columns.str.strip()

print("데이터 로드 완료. 행 개수:", len(df_stops))
print("컬럼 목록:", df_stops.columns.tolist()) # 컬럼명이 정상인지 확인

# 학습에 사용할 좌표 데이터 (이제 정상적으로 lat을 찾을 수 있습니다)
X = df_stops[['lat', 'lon']]

# ---------------------------------------------------------
# 2. 엘보우 기법 (Elbow Method) - 최적의 k 찾기
# ---------------------------------------------------------
inertias = []
# 데이터가 18개뿐이므로 클러스터 개수는 최대 10개까지만 테스트
K_range = range(1, 11)

for k in K_range:
    kmeans_test = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans_test.fit(X)
    inertias.append(kmeans_test.inertia_)

# 엘보우 그래프 시각화
plt.figure(figsize=(10, 5))
plt.plot(K_range, inertias, 'bx-')
plt.xlabel('Number of Clusters (k)')
plt.ylabel('Inertia (SSE)')
plt.title('The Elbow Method using Inertia')
plt.grid(True)
output_path = os.path.join(VIS_DIR, "elbow_kmeans.png")
plt.savefig(output_path, dpi=200, bbox_inches="tight")
plt.show()