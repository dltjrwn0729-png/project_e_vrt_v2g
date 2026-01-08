import xpress as xp
import numpy as np
import pandas as pd
import folium
import requests
import polyline
import time
import os
from datetime import datetime

# =========================================================
# 1. 경로 자동 설정 (os 모듈 활용)
# =========================================================
# 현재 파일(smart_choice_master.py)의 위치를 기준으로 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # py/ 폴더
PROJECT_ROOT = os.path.dirname(BASE_DIR)  # 프로젝트 루트 (e_vrt_v2g_project/)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")  # data/ 폴더
VISUAL_DIR = os.path.join(PROJECT_ROOT, "visualization")  # visualization/ 폴더

# 저장용 폴더가 없으면 자동 생성
os.makedirs(VISUAL_DIR, exist_ok=True)

# Xpress 초기화
try:
    xp.init('c:/xpressmp/bin/xpauth.xpr')
except:
    pass


class CheonanSmartCity_Master_Final:
    def __init__(self, node_file, passenger_file, visual_dir):
        print("--- [System] 마스터 통합 모델 가동 (Smart Choice 적용 버전) ---")
        self.visual_dir = visual_dir

        # 데이터 로드
        self.df_base = pd.read_csv(node_file)
        self.df_passengers = pd.read_csv(passenger_file)
        self.df = pd.concat([self.df_base, self.df_passengers], ignore_index=True)

        self.N = len(self.df)
        self.hubs = self.df[self.df['location_type'] == 0].index.tolist()
        self.stops = self.df[self.df['location_type'] == 1].index.tolist()
        self.users = self.df[self.df['location_type'] == 2].index.tolist()
        self.user_dest = {u: int(self.df.at[u, 'dest_id']) for u in self.users}

        self.dist = self._build_dist_matrix()
        self.MAX_DIST = 6000
        self.arcs = self._build_valid_arcs()

        self.V = 12
        self.M = 5000  # Big-M
        self.prob = xp.problem("Cheonan_Master_Final")

    def _build_dist_matrix(self):
        mat = np.zeros((self.N, self.N))
        coords = self.df[['lat', 'lon']].values
        for i in range(self.N):
            for j in range(self.N):
                if i != j:
                    # 위경도 -> 미터 변환 근사치
                    mat[i, j] = np.sqrt(
                        ((coords[i][0] - coords[j][0]) * 111000) ** 2 + ((coords[i][1] - coords[j][1]) * 88800) ** 2)
        return mat

    def _build_valid_arcs(self):
        valid = set()
        for i in range(self.N):
            for j in range(self.N):
                if i == j: continue
                if i in self.hubs or j in self.hubs or self.dist[i, j] <= self.MAX_DIST:
                    valid.add((i, j))
        for u, d in self.user_dest.items():
            valid.add((u, d))
        return list(valid)

    def build_model(self):
        print("--- [Logic] 수리적 모델 구축 (AI Smart Choice 모드) ---")
        p = self.prob

        # 변수 정의
        self.x = {(i, j, v): p.addVariable(vartype=xp.binary, name=f"x_{i}_{j}_{v}") for (i, j) in self.arcs for v in
                  range(self.V)}
        self.z = {u: p.addVariable(vartype=xp.binary, name=f"z_{u}") for u in self.users}
        self.t = {(i, v): p.addVariable(lb=0, ub=self.M) for i in range(self.N) for v in range(self.V)}
        self.dis = {(h, v): p.addVariable(lb=0, ub=20.0) for h in self.hubs for v in range(self.V)}

        # 목적 함수: (승객 가치) + (V2G 방전 가치) - (주행 거리 비용)
        p.setObjective(
            xp.Sum(50000 * self.z[u] for u in self.users) +
            xp.Sum(200 * self.dis[h, v] for h in self.hubs for v in range(self.V)) -
            xp.Sum(0.15 * self.dist[i, j] * self.x[i, j, v] for (i, j) in self.arcs for v in range(self.V)),
            sense=xp.maximize
        )

        # 제약 조건 설정
        for v in range(self.V):
            p.addConstraint(xp.Sum(self.x[h, j, v] for (h, j) in self.arcs if h in self.hubs) == 1)
            p.addConstraint(xp.Sum(self.x[i, h, v] for (i, h) in self.arcs if h in self.hubs) == 1)

            for k in range(self.N):
                if k not in self.hubs:
                    p.addConstraint(xp.Sum(self.x[i, k, v] for (i, k2) in self.arcs if k2 == k) ==
                                    xp.Sum(self.x[k, j, v] for (k2, j) in self.arcs if k2 == k))

            for (i, j) in self.arcs:
                p.addConstraint(self.t[j, v] >= self.t[i, v] + (self.dist[i, j] / 500) - self.M * (1 - self.x[i, j, v]))

        for u in self.users:
            p.addConstraint(
                xp.Sum(self.x[i, u, v] for (i, u_idx) in self.arcs if u_idx == u for v in range(self.V)) <= 1)
            p.addConstraint(
                self.z[u] == xp.Sum(self.x[i, u, v] for (i, u_idx) in self.arcs if u_idx == u for v in range(self.V)))

            req_time = self.df.at[u, 'request_time']
            d = self.user_dest[u]

            # [Smart Choice 로직] 대안 수단(버스/도보) 대비 우위성 판단
            alt_transport_time = (self.dist[u, d] / 250) + 10

            for v in range(self.V):
                is_p = xp.Sum(self.x[i, u, v] for (i, idx) in self.arcs if idx == u)
                p.addConstraint(self.t[u, v] >= req_time * is_p)
                p.addConstraint(self.t[u, v] <= (req_time + 60) * is_p + self.M * (1 - is_p))
                p.addConstraint(xp.Sum(self.x[i, d, v] for (i, d2) in self.arcs if d2 == d) >= is_p)
                p.addConstraint((self.t[d, v] - req_time) <= alt_transport_time + self.M * (1 - is_p))

    def _get_osrm_path(self, i, j):
        try:
            time.sleep(0.1)
            url = f"http://router.project-osrm.org/route/v1/driving/{self.df.at[i, 'lon']},{self.df.at[i, 'lat']};{self.df.at[j, 'lon']},{self.df.at[j, 'lat']}?overview=full"
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return polyline.decode(r.json()['routes'][0]['geometry'])
        except:
            pass
        return [[self.df.at[i, 'lat'], self.df.at[i, 'lon']], [self.df.at[j, 'lat'], self.df.at[j, 'lon']]]

    def solve_and_generate_results(self):
        print("--- [Solver] 최적화 실행 중 ---")
        self.prob.controls.miprelstop = 0.15
        self.prob.controls.maxtime = 120
        self.prob.solve()

        # 결과 저장 경로 설정
        map_path = os.path.join(self.visual_dir, "cheonan_smart_choice_map.html")
        excel_path = os.path.join(self.visual_dir, "천안시_최종_결과보고서.xlsx")

        m = folium.Map(location=[36.815, 127.114], zoom_start=13, tiles='cartodbpositron')
        colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'cadetblue', 'darkpurple', 'pink', 'lightblue',
                  'lightgreen', 'gray']

        # 마커 추가
        for idx, row in self.df.iterrows():
            color = 'black' if row['location_type'] == 0 else ('blue' if row['location_type'] == 1 else 'red')
            icon_type = 'star' if row['location_type'] == 0 else ('info-sign' if row['location_type'] == 1 else 'user')
            folium.Marker([row['lat'], row['lon']], tooltip=f"Type {int(row['location_type'])} - ID {idx}",
                          icon=folium.Icon(color=color, icon=icon_type)).add_to(m)

        passenger_verify_logs = []
        for v in range(self.V):
            curr = -1
            for h in self.hubs:
                if any(self.prob.getSolution(self.x[h, j, v]) > 0.5 for (h_idx, j) in self.arcs if h_idx == h):
                    curr = h
                    break
            if curr == -1: continue

            v_path_nodes = [curr]
            full_coords = []
            visited = {curr}
            while True:
                next_node = -1
                for (i, j) in self.arcs:
                    if i == curr and self.prob.getSolution(self.x[i, j, v]) > 0.5:
                        next_node = j
                        break
                if next_node == -1 or next_node in visited: break
                full_coords.extend(self._get_osrm_path(curr, next_node))
                v_path_nodes.append(next_node)
                visited.add(next_node)
                curr = next_node
                if curr in self.hubs: break

            if full_coords:
                folium.PolyLine(full_coords, color=colors[v % 12], weight=4, opacity=0.7).add_to(m)

            # 로그 수집
            for u in self.users:
                if self.prob.getSolution(self.z[u]) > 0.5 and u in v_path_nodes:
                    dest = self.user_dest[u]
                    try:
                        u_idx, d_idx = v_path_nodes.index(u), v_path_nodes.index(dest)
                        path_chain = v_path_nodes[u_idx: d_idx + 1]
                        passenger_verify_logs.append({
                            '승객ID': self.df.at[u, 'passenger_id'],
                            '이동경로(노드순서)': " -> ".join(map(str, path_chain)),
                            '배차차량': f"e-DRT_{v + 1:02d}"
                        })
                    except:
                        pass

        m.save(map_path)
        with pd.ExcelWriter(excel_path) as writer:
            pd.DataFrame(passenger_verify_logs).to_excel(writer, sheet_name='승객별_경로_검증', index=False)
            self.df.to_excel(writer, sheet_name='위경도좌표정보', index=True)

        print(f"✅ 결과물이 visualization 폴더에 생성되었습니다.")
        print(f"📍 지도: {map_path}")
        print(f"📍 보고서: {excel_path}")


if __name__ == "__main__":
    # 데이터 경로 자동 조합
    hub_file = os.path.join(DATA_DIR, "hub_and_stop_locations.csv")
    psg_file = os.path.join(DATA_DIR, "passenger_data.csv")

    # 모델 초기화 (경로 전달)
    model = CheonanSmartCity_Master_Final(hub_file, psg_file, VISUAL_DIR)
    model.build_model()
    model.solve_and_generate_results()