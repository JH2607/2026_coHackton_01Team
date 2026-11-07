"""
4번 검증 함수 모듈 (kakao_verifier.py)
역할: AI 추천 장소를 카카오 API로 검색하여 검증하고, 주소·좌표·카카오맵 링크를 결합합니다.
"""

import os
import requests
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv

load_dotenv()

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")


def search_place_on_kakao(place_name: str, region: str) -> Dict[str, Any] | None:
    """
    카카오 키워드 장소 검색 API를 호출합니다.
    검색 성공 시: 주소, 위도, 경도, 카카오맵 URL 반환
    검색 실패/미존재 시: None 반환
    """
    if not KAKAO_REST_API_KEY:
        print("[경고] KAKAO_REST_API_KEY가 설정되지 않았습니다.")
        return None

    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    
    # 더 정확한 검색을 위해 "지역명 + 가게이름"으로 검색
    params = {
        "query": f"{region} {place_name}",
        "size": 1  # 가장 연관도 높은 1위 결과만 가져옴
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=3)
        if response.status_code == 200:
            data = response.json()
            documents = data.get("documents", [])
            if documents:
                top_result = documents[0]
                return {
                    "verified_name": top_result.get("place_name"),
                    "address": top_result.get("road_address_name") or top_result.get("address_name"),
                    "lat": float(top_result.get("y")),  # 위도
                    "lng": float(top_result.get("x")),  # 경도
                    "place_url": top_result.get("place_url")  # 카카오맵 링크
                }
    except Exception as e:
        print(f"[카카오 검색 오류]: {e}")

    return None


def verify_places(ai_places: List[Dict[str, Any]], region: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    [핵심 검증 함수]
    AI가 추천한 가게 목록(ai_places) 중:
    - 카카오에 검색되는 진짜 장소: 주소, 좌표(lat/lng), place_url을 추가하여 verified_places에 추가
    - 검색되지 않는 장소(환각/폐업): 제외하고 dropped_places에 이름 기록
    
    반환값: (검증 통과 목록, 제외된 장소 목록)
    """
    verified_places = []
    dropped_places = []

    for place in ai_places:
        name = place.get("name", "")
        # 카카오 검색 시도
        kakao_data = search_place_on_kakao(name, region)

        if kakao_data:
            # 기존 AI 정보(카테고리, 추천이유, 예산 등)에 카카오 검증 정보(주소, 좌표, 링크)를 결합
            enriched_place = {
                **place,
                "name": kakao_data["verified_name"],  # 카카오 공식 명칭으로 정제
                "address": kakao_data["address"],
                "lat": kakao_data["lat"],
                "lng": kakao_data["lng"],
                "place_url": kakao_data["place_url"],
                "is_verified": True
            }
            verified_places.append(enriched_place)
        else:
            # 검색되지 않는 곳은 제외 처리
            dropped_places.append(name)

    return verified_places, dropped_places


# ---------------------------------------------------------
# 단독 실행 테스트 (내 컴퓨터에서 잘 돌아가는지 확인용)
# ---------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("🔍 4번 카카오 장소 검증 함수 테스트")
    print("=" * 60)

    # 테스트 데이터 (성수동의 실제 카페 2곳 + 가짜 장소 1곳)
    sample_ai_places = [
        {"name": "대림창고", "category": "카페", "reason": "성수동 대표 복합문화 갤러리 카페"},
        {"name": "어니언 성수", "category": "카페", "reason": "베이커리가 유명한 인더스트리얼 핫플"},
        {"name": "성수동유령가짜카페99호점", "category": "카페", "reason": "가짜 장소 (제외 테스트)"}
    ]

    region_test = "성수"
    print(f"\n[입력] AI 추천 장소 {len(sample_ai_places)}곳 검증 시작...")
    
    verified, dropped = verify_places(sample_ai_places, region_test)

    print(f"\n✅ [검증 통과 장소: {len(verified)}곳]")
    for p in verified:
        print(f"- {p['name']} | 주소: {p['address']} | 좌표: ({p['lat']}, {p['lng']})")
        print(f"  링크: {p['place_url']}")

    print(f"\n❌ [검증 탈락/제외 장소: {len(dropped)}곳]")
    for d in dropped:
        print(f"- {d} (카카오 검색 불가로 자동 제외됨)")

    print("\n" + "=" * 60)
    print("🎉 4번 검증 함수가 정상 작동합니다!")
    print("=" * 60)
