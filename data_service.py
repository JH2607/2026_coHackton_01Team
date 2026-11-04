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
    results = []

    for place in get_places_by_region(region):
        price_text = place.get("price_krw", "").strip()

        # 가격 미확인 장소 제외
        if not price_text:
            continue

        # 잘못된 가격 형식 제외
        try:
            price = int(price_text)
        except ValueError:
            continue

        if 0 <= price <= max_price:
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

def get_candidate_places(user_input: dict) -> list[dict]:
    """AI 담당자에게 넘길, 검증 가능한 예산·카테고리 조건 통과 후보.

    이 함수는 현재 ui.py가 바로 호출하지 않는, 추후 AI 연결용 함수입니다.
    """
    results = []
    for place in get_places_by_region(user_input["region"]):
        if place["category"] not in user_input["categories"]:
            continue
        price = place["price_krw"].strip()
        if not price:
            continue  # 미확인 가격을 무료(0원)로 오인하지 않도록 제외
        try:
            amount = int(price)
        except ValueError:
            continue
        if 0 <= amount <= user_input["max_price"]:
            results.append(place)
    return results
    
if __name__ == "__main__":
    seongsu = get_places_by_region("성수")
    hongdae = get_places_by_region("홍대")

    print("성수:", len(seongsu), "곳")
    print("홍대:", len(hongdae), "곳")

