"""데이터 및 검증 담당 파일.

개발할 내용: CSV/API 데이터 불러오기, 검색·전처리, 검증
"""

# TODO: 주제에 맞는 데이터 형식과 저장 방법을 정한 뒤 구현하세요.
# Syntitan을 통한 데이터 진단/평가 결과도 담당자가 정리해 주세요.

import csv
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_PATH = DATA_DIR / "places.csv"

def load_csv(filename):
    path = DATA_DIR / filename

    with open(path, encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def get_places(region, max_price):
    places = load_csv("places.csv")
    results = []

    for place in places:
        if place["region"] != region:
            continue

        # 가격을 모르는 장소는 우선 제외
        if not place["price"].strip():
            continue

        if int(place["price"]) <= max_price:
            results.append(place)

    return results


def get_travelers(region):
    travelers = load_csv("travelers_demo.csv")

    return [
        traveler
        for traveler in travelers
        if traveler["region"] == region
        and traveler["match_opt_in"].lower() == "true"
    ]

def get_places_by_region(region):
    with open(DATA_DIR / "places.csv", encoding="utf-8-sig", newline="") as file:
        places = list(csv.DictReader(file))

    return [
        place for place in places
        if place["region"] == region
    ]

if __name__ == "__main__":
    seongsu = get_places_by_region("성수")
    hongdae = get_places_by_region("홍대")

    print("성수:", len(seongsu), "곳")
    print("홍대:", len(hongdae), "곳")

