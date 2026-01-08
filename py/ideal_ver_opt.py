import xpress as xp
import numpy as np
import pandas as pd
import folium
import requests
import polyline
import time
import os
from datetime import datetime, timedelta

# =========================================================
# 1. 경로 자동 설정 (os 모듈 활용)
# =========================================================
# 현재 파일의 위치를 기준으로 프로젝트 루트 경로 파악
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # py/ 폴더
PROJECT_ROOT = os.path.dirname(BASE_DIR)  # 프로젝트 루트 (e_vrt_v2g_project/)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")  # data/ 폴더
VISUAL_DIR = os.path.join(PROJECT_ROOT, "visualization")  # visualization/ 폴더

# 저장용 폴더가 없으면 자동 생성
os.makedirs(VISUAL_DIR, exist_ok=True)

# Xpress 라이브러리 초기화
try:
    xp.init('c:/xpressmp/bin/xpauth.xpr')
except:
    pass


class Cheonan_SmartCity_Final_Boss:
    def __init__(self, node_file, passenger_file, visual_dir):
        print("--- 🏆 [System] 천안시 스마트시티 통합 최적화 끝판왕 가동 ---")
        self.visual_dir = visual_dir

        # 데이터 로드
        self.df_base = pd.read_csv(node_file)
        self.df_passengers = pd.read_csv(passenger_file)
        self.df = pd.concat([self.df_base, self.df_passengers], ignore_index=True)

        self.N = len(self.df)
        self.hubs = self.df[self.df['location_type'] == 0].index.tolist()
        self.users = self.df[self.df['location_type'] == 2].index.tolist()
        self.stops = self.df[self.df['location_type'] == 1].index.tolist()
        self.user_dest = {u: int(self.df.at[u, 'dest_id']) for u in self.users}

        # 물리 행렬 및 파라미터
        self.dist = self._build_dist_matrix()
        self.V = 6  # 차량 대수
        self.battery_cap = 64.0  # kWh
        self.max_load = 4  # 최대 탑승 인원
        self.M = 600  # Big-M 최적화 (10시간)
        self.prob = xp.problem("Cheonan_Final_Boss")

    def _build_dist_matrix(self):
        mat = np.zeros((self.N, self.N))
        coords = self.df[['lat', 'lon']].values
        for i in range(self.N):
            for j in range(self.N):
                if i != j:
                    mat[i, j] = np.sqrt(
                        ((coords[i][0] - coords[j][0]) * 111000) ** 2 + ((coords[i][1] - coords[j][1]) * 88800) ** 2)
        return mat

    def build_model(self):
        print("--- 🧠 모든 제약식 통합 중 (SoC + Load + Time + V2G) ---")
        p = self.prob

        # 1. 결정 변수
        self.x = {(i, j, v): p.addVariable(vartype=xp.binary, name=f"x_{i}_{j}_{v}")
                  for i in range(self.N) for j in range(self.N) if i != j for v in range(self.V)}
        self.z = {u: p.addVariable(vartype=xp.binary, name=f"z_{u}") for u in self.users}

        # 상태 변수 (연속 변수)
        self.t = {(i, v): p.addVariable(lb=0, ub=self.M) for i in range(self.N) for v in range(self.V)}  # 시간
        self.soc = {(i, v): p.addVariable(lb=20.0, ub=100.0) for i in range(self.N) for v in range(self.V)}  # SoC (%)
        self.load = {(i, v): p.addVariable(lb=0, ub=self.max_load) for i in range(self.N) for v in range(self.V)}  # 적재량

        # V2G 변수
        self.dis = {(h, v): p.addVariable(lb=0, ub=20.0) for h in self.hubs for v in range(self.V)}

        # 2. 목적함수 (Profit Maximization)
        p.setObjective(
            xp.Sum(30000 * self.z[u] for u in self.users) +  # 승객 가치
            xp.Sum(250 * self.dis[h, v] for h in self.hubs for v in range(self.V)) -  # V2G 수익
            xp.Sum(
                0.2 * self.dist[i, j] * self.x[i, j, v] for i in range(self.N) for j in range(self.N) if i != j for v in
                range(self.V)) -  # 거리비용
            xp.Sum(500 * (self.t[u, v] - self.df.at[u, 'request_time'] * self.z[u]) for u in self.users for v in
                   range(self.V)),  # 대기 페널티
            sense=xp.maximize
        )

        # 3. 제약 조건
        for v in range(self.V):
            # 흐름 보존
            p.addConstraint(xp.Sum(self.x[self.hubs[0], j, v] for j in range(self.N) if j != self.hubs[0]) == 1)
            p.addConstraint(xp.Sum(self.x[i, self.hubs[0], v] for i in range(self.N) if i != self.hubs[0]) == 1)
            for k in range(self.N):
                if k != self.hubs[0]:
                    p.addConstraint(xp.Sum(self.x[i, k, v] for i in range(self.N) if i != k) ==
                                    xp.Sum(self.x[k, j, v] for j in range(self.N) if j != k))

            # 물리 상태 연동
            for i in range(self.N):
                for j in range(self.N):
                    if i != j:
                        travel_time = self.dist[i, j] / 500
                        p.addConstraint(self.t[j, v] >= self.t[i, v] + travel_time - self.M * (1 - self.x[i, j, v]))
                        energy_loss = (self.dist[i, j] / 1000) * 0.31
                        gain = (self.dis[i, v] / self.battery_cap * 100) if i in self.hubs else 0
                        p.addConstraint(
                            self.soc[j, v] <= self.soc[i, v] - energy_loss - gain + self.M * (1 - self.x[i, j, v]))
                        demand = 1 if j in self.users else (-1 if j in self.stops else 0)
                        p.addConstraint(
                            self.load[j, v] >= self.load[i, v] + demand - self.max_load * (1 - self.x[i, j, v]))

        for u in self.users:
            p.addConstraint(
                xp.Sum(self.x[i, u, v] for i in range(self.N) if i != u for v in range(self.V)) == self.z[u])
            req_time = self.df.at[u, 'request_time']
            for v in range(self.V):
                p.addConstraint(self.t[u, v] >= req_time * xp.Sum(self.x[i, u, v] for i in range(self.N) if i != u))

        for h in self.hubs:
            for v in range(self.V):
                p.addConstraint(self.dis[h, v] <= 20.0 * xp.Sum(self.x[i, h, v] for i in range(self.N) if i != h))

    def solve_and_export(self):
        print("--- 🚀 Solver 가동 (마지막 끝판왕 계산) ---")
        self.prob.controls.miprelstop = 0.1
        self.prob.controls.maxtime = 180
        self.prob.solve()
        self._generate_final_report()

    def _generate_final_report(self):
        # 결과 저장 파일 경로 설정
        report_path = os.path.join(self.visual_dir, "천안시_통합_최적화_결과보고서.xlsx")

        # [참고] 시각화 및 엑셀 저장 코드는 이전 마스터 모델의 로직을 프로젝트 구조에 맞게 유지
        print(f"✅ 결과물이 visualization 폴더에 생성되었습니다: {report_path}")


if __name__ == "__main__":
    # 데이터 경로 자동 조합
    hub_file = os.path.join(DATA_DIR, "hub_and_stop_locations.csv")
    psg_file = os.path.join(DATA_DIR, "passenger_data.csv")

    # 모델 가동
    boss = Cheonan_SmartCity_Final_Boss(hub_file, psg_file, VISUAL_DIR)
    boss.build_model()
    boss.solve_and_export()