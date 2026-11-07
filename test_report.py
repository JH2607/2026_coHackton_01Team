"""
5번: AI 추천 장소 검증 테스트 및 보고서용 통계 생성 스크립트 (test_report.py)
역할: 다양한 지역/조건 7개에 대해 카카오 API 검증을 수행하고, 보고서용 표를 자동 출력합니다.
"""

import json
from kakao_verifier import verify_places

# ---------------------------------------------------------
# 1. 테스트할 7가지 조건과 추천 장소 데이터
# (※ 추후 3번 팀원이 완성한 AI 함수가 있으면 바로 교체 가능하도록 설계됨)
# ---------------------------------------------------------
TEST_SCENARIOS = [
    {
        "id": 1,
        "region": "성수",
        "theme": "오후 감성 카페 & 전시 투어",
        "places": [
            {"name": "대림창고", "category": "카페"},
            {"name": "어니언 성수", "category": "카페"},
            {"name": "성수연방", "category": "복합문화공간"},
            {"name": "성수동유령가짜팝업", "category": "팝업스토어"}  # 의도적 가짜 장소
        ]
    },
    {
        "id": 2,
        "region": "홍대",
        "theme": "저녁 가성비 맛집 & 소품샵",
        "places": [
            {"name": "테일러커피 서교점", "category": "카페"},
            {"name": "카카오프렌즈 홍대플래그십스토어", "category": "소품샵"},
            {"name": "연남동 존재하지않는식당", "category": "음식점"}  # 의도적 가짜 장소
        ]
    },
    {
        "id": 3,
        "region": "을지로",
        "theme": "레트로 힙플레이스 탐방",
        "places": [
            {"name": "을지면옥", "category": "음식점"},
            {"name": "호랑이커피", "category": "카페"},
            {"name": "만선호프", "category": "음식점"}
        ]
    },
    {
        "id": 4,
        "region": "강남",
        "theme": "도심 속 힐링 & 북카페",
        "places": [
            {"name": "일상비일상의틈", "category": "복합문화공간"},
            {"name": "스타필드 코엑스몰 별마당도서관", "category": "문화시설"},
            {"name": "강남역상상속비밀카페", "category": "카페"}  # 의도적 가짜 장소
        ]
    },
    {
        "id": 5,
        "region": "종로",
        "theme": "익선동 한옥 골목 투어",
        "places": [
            {"name": "청수당", "category": "카페"},
            {"name": "온천집 익선", "category": "음식점"},
            {"name": "호텔세느장", "category": "카페"}
        ]
    },
    {
        "id": 6,
        "region": "연남",
        "theme": "연트럴파크 산책 & 디저트",
        "places": [
            {"name": "랜디스도넛 연남점", "category": "디저트"},
            {"name": "테일러커피 연남점", "category": "카페"}
        ]
    },
    {
        "id": 7,
        "region": "제주",
        "theme": "애월 오션뷰 카페 & 향토음식",
        "places": [
            {"name": "카페 봄날", "category": "카페"},
            {"name": "돈사돈 본점", "category": "음식점"},
            {"name": "한라산구름솜사탕카페", "category": "디저트"}  # 의도적 가짜 장소
        ]
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
        ai_places = item["places"]

        # 4번 검증 함수 호출 (진짜 카카오 API로 실시간 확인!)
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
