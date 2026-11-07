"""
5번: AI 추천 장소 검증 테스트 및 보고서용 통계 생성 스크립트 (test_report.py)
역할: 3번 AI 추천과 4번 카카오 API 검증을 결합하여, 입력 7개에 대한 검증 통계 표를 자동 생성합니다.
"""

from kakao_verifier import verify_places
from ai_service import generate_travel_recommendation

# ---------------------------------------------------------
# 1. 테스트할 7가지 사용자 여행 조건 (입력 시나리오)
# ---------------------------------------------------------
TEST_SCENARIOS = [
    {
        "id": 1,
        "region": "성수",
        "theme": "오후 감성 카페 & 전시 투어",
        "max_price": 25000,
        "categories": ["카페", "전시", "팝업스토어"]
    },
    {
        "id": 2,
        "region": "홍대",
        "theme": "저녁 가성비 맛집 & 소품샵",
        "max_price": 15000,
        "categories": ["음식점", "소품샵"]
    },
    {
        "id": 3,
        "region": "을지로",
        "theme": "레트로 힙플레이스 탐방",
        "max_price": 30000,
        "categories": ["음식점", "카페"]
    },
    {
        "id": 4,
        "region": "강남",
        "theme": "도심 속 힐링 & 북카페",
        "max_price": 20000,
        "categories": ["카페", "문화시설"]
    },
    {
        "id": 5,
        "region": "종로",
        "theme": "익선동 한옥 골목 투어",
        "max_price": 25000,
        "categories": ["카페", "음식점"]
    },
    {
        "id": 6,
        "region": "연남",
        "theme": "연트럴파크 산책 & 디저트",
        "max_price": 18000,
        "categories": ["카페", "디저트"]
    },
    {
        "id": 7,
        "region": "제주",
        "theme": "애월 오션뷰 카페 & 향토음식",
        "max_price": 35000,
        "categories": ["카페", "음식점"]
    }
]


def run_benchmark_tests():
    print("=" * 80)
    print("📊 [5번] AI 추천 장소 카카오 API 신뢰성 검증 테스트 시작")
    print("=" * 80)

    total_ai_count = 0
    total_verified_count = 0
    total_dropped_count = 0

    # 마크다운 표 헤더
    print("\n### 📋 카카오 API 장소 검증 테스트 결과표 (보고서/발표자료용)\n")
    print("| 번호 | 지역 | 여행 테마 | AI 추천 수 | 카카오 검증 통과 | 제외된 곳(가짜/폐업) | 통과율 |")
    print("|:---:|:---:|:---|:---:|:---:|:---|:---:|")

    for item in TEST_SCENARIOS:
        test_id = item["id"]
        region = item["region"]
        theme = item["theme"]

        # ① [3번 AI 연동] 실시간 추천 장소 생성
        user_input = {
            "region": region,
            "date": "2026-11-14",
            "start_time": "13:00",
            "end_time": "17:00",
            "max_price": item["max_price"],
            "categories": item["categories"]
        }
        ai_res = generate_travel_recommendation(user_input)
        ai_places = ai_res.get("data", {}).get("places", [])

        # ② [4번 카카오 연동] 카카오 API로 실시간 장소 검증!
        verified, dropped = verify_places(ai_places, region)

        ai_cnt = len(ai_places)
        v_cnt = len(verified)
        d_cnt = len(dropped)
        pass_rate = (v_cnt / ai_cnt * 100) if ai_cnt > 0 else 0

        total_ai_count += ai_cnt
        total_verified_count += v_cnt
        total_dropped_count += d_cnt

        dropped_names = ", ".join(dropped) if dropped else "없음"
        print(f"| {test_id} | {region} | {theme} | {ai_cnt}곳 | **{v_cnt}곳** | {dropped_names} | {pass_rate:.1f}% |")

    overall_pass_rate = (total_verified_count / total_ai_count * 100) if total_ai_count > 0 else 0

    print("\n" + "=" * 80)
    print("📌 [테스트 종합 통계]")
    print(f"- 총 테스트 시나리오: {len(TEST_SCENARIOS)}개 지역")
    print(f"- AI 총 추천 장소: {total_ai_count}곳")
    print(f"- 카카오 API 검증 통과 (실존 장소): {total_verified_count}곳")
    print(f"- 필터링된 환각/폐업 장소: {total_dropped_count}곳")
    print(f"- **최종 검증 통과율: {overall_pass_rate:.1f}%**")
    print("=" * 80)


if __name__ == "__main__":
    run_benchmark_tests()
