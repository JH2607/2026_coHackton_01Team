"""데이터 및 검증 담당 파일.

개발할 내용: CSV/API 데이터 불러오기, 검색·전처리, 검증
"""

# TODO: 주제에 맞는 데이터 형식과 저장 방법을 정한 뒤 구현하세요.
# Syntitan을 통한 데이터 진단/평가 결과도 담당자가 정리해 주세요.

import csv
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

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
    travelers = load_csv("travelers.csv")

    return [
        traveler
        for traveler in travelers
        if traveler["region"] == region
        and traveler["match_opt_in"].lower() == "true"
    ]