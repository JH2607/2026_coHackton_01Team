"""AI 기능 담당 파일 (OpenRouter API 등).

개발할 내용: AI API 연동, 프롬프트, 응답 검증
"""

# TODO: 팀원들과 함수 이름/입출력을 합의한 다음 구현하세요.
# 중요: API 키를 코드에 직접 쓰거나 GitHub에 올리지 마세요.

import os
import json
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from openai import OpenAI
# 1. 환경 변수 로드 (.env 파일에서 API 키 읽기)
load_dotenv()
# 로깅 설정 (에러 및 상태 추적용)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
# ---------------------------------------------------------
# OpenRouter API 연결 및 클라이언트 초기화
# ---------------------------------------------------------
def get_openrouter_client() -> tuple[OpenAI, str]:
    """
    OpenRouter API 연결을 위한 OpenAI SDK 클라이언트를 생성합니다.
    - 환경변수 우선순위: OPENROUTER_API_KEY -> OPENAI_API_KEY
    - 기본 모델: google/gemini-2.0-flash-001 (속도, 비용, 한국어 성능 최적화)
    """
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.getenv("LLM_MODEL", "google/gemini-2.0-flash-001")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY가 설정되지 않았습니다. .env 파일을 확인해 주세요.")
    client = OpenAI(
        api_key=api_key or "DUMMY_KEY_FOR_LOCAL_TEST",
        base_url=base_url,
        default_headers={
            "HTTP-Referer": "http://localhost:8501",  # OpenRouter 대시보드 표시용
            "X-Title": "2026_coHackton_01Team AI Service"
        }
    )
    return client, model
# ---------------------------------------------------------
# 서비스 목적에 맞는 기본 프롬프트 정의
# ---------------------------------------------------------
# (1) 맞춤형 여행 장소 추천 프롬프트 (ui.py의 폼 입력 데이터와 호환)
RECOMMEND_SYSTEM_PROMPT = """
너는 국내 로컬 여행 코스 전문 AI 플래너다.
사용자의 여행 지역(region), 여행 시간대(start_time ~ end_time), 1곳당 최대 예산(max_price), 관심 분야(categories)를 반영하여 최적의 추천 코스를 작성한다.
[작성 규칙]
1. 사용자가 지정한 지역과 장소 1곳당 최대 예산 한도를 엄격히 준수한다.
2. 장소 목록(places)은 사용자의 활동 시간 동안 방문하기 적합한 순서로 2~4곳 추천한다.
3. 반드시 아래 JSON 형식으로만 응답하며, 마크다운 코드블록(```json) 없이 순수 JSON 문자열만 출력한다.
[반환 JSON 규격]
{
  "summary": "추천 코스 전체 요약 한 줄 (예: 성수동에서 즐기는 오후의 감성 카페 및 전시 투어)",
  "total_estimated_cost": 숫자(전체 예상 비용 합계, 원 단위),
  "places": [
    {
      "name": "장소명",
      "category": "카페 | 전시 | 음식점 | 소품샵 등 카테고리",
      "price_krw": "숫자 문자열 (예: '15000' 또는 '0')",
      "duration_min": "소요 예상 시간(분 단위 숫자 문자열, 예: '60')",
      "address": "장소 개략 위치 또는 주소 (예: 서울 성동구 성수동2가)",
      "tags": "해시태그 키워드 (|로 구분, 예: 감성카페|디저트|포토존)",
      "reason": "이 장소를 추천하는 구체적인 이유"
    }
  ]
}
"""
# (2) 여행객 매칭 시스템 프롬프트 (동행 찾기용)
MATCHING_SYSTEM_PROMPT = """
너는 여행객 간의 일정 및 취향을 분석하여 최적의 동행 시너지를 제안하는 AI 매칭 전문가다.
두 사용자의 여행 지역, 겹치는 시간대, 관심사(interests)를 분석하여 매칭 점수와 함께하기 좋은 활동을 제안한다.
[작성 규칙]
1. 두 여행객의 공통 관심사를 바탕으로 구체적인 동행 활동을 제안한다.
2. 반드시 아래 JSON 형식으로만 응답하며, 마크다운 코드블록 없이 순수 JSON 문자열만 출력한다.
[반환 JSON 규격]
{
  "match_score": 숫자 (0 ~ 100점 사이 정수),
  "common_interests": ["공통 관심사1", "공통 관심사2"],
  "recommended_activity": "겹치는 시간 동안 함께하기 좋은 구체적인 활동 제안",
  "match_reason": "두 여행객의 성향과 일정을 고려한 매칭 추천 사유"
}
"""
# ---------------------------------------------------------
# API 오류 처리 (Fallback 메커니즘)
# ---------------------------------------------------------
def _get_fallback_recommendation(user_input: Dict[str, Any]) -> Dict[str, Any]:
    """API 호출 실패, 키 누락, 네트워크 오류 시 서비스가 멈추지 않도록 기본 추천 데이터 반환"""
    region = user_input.get("region", "선택 지역")
    return {
        "status": "fallback",
        "message": "현재 AI 서버 연결이 원활하지 않아 기본 추천 코스를 안내해 드립니다.",
        "data": {
            "summary": f"{region} 지역의 인기 추천 명소 코스입니다.",
            "total_estimated_cost": 25000,
            "places": [
                {
                    "name": f"{region} 대표 로컬 카페",
                    "category": "카페",
                    "price_krw": "8000",
                    "duration_min": "60",
                    "address": f"서울 {region} 중심거리",
                    "tags": "인기명소|커피맛집|분위기",
                    "reason": "지역 방문 시 가장 만족도가 높은 대표 휴식 공간입니다."
                },
                {
                    "name": f"{region} 문화복합공간",
                    "category": "전시",
                    "price_krw": "15000",
                    "duration_min": "90",
                    "address": f"서울 {region} 문화거리",
                    "tags": "전시|문화체험|포토존",
                    "reason": "다양한 볼거리와 감각적인 전시를 즐기기 좋습니다."
                }
            ]
        }
    }
def _get_fallback_matching() -> Dict[str, Any]:
    """매칭 분석 실패 시 반환되는 기본 Fallback 데이터"""
    return {
        "status": "fallback",
        "message": "AI 매칭 분석 중 오류가 발생하여 기본 매칭 정보를 반환합니다.",
        "data": {
            "match_score": 75,
            "common_interests": ["여행", "맛집 탐방"],
            "recommended_activity": "인근 카페에서 가볍게 커피 한 잔 하며 여행 일정 공유하기",
            "match_reason": "동일 지역 및 겹치는 시간대에 일정이 있는 여행객입니다."
        }
    }
def _parse_llm_json(raw_text: str) -> Dict[str, Any]:
    """LLM 응답에서 혹시 포함될 수 있는 마크다운 코드블록(```json)을 제거하고 안전하게 파싱"""
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json"):].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[len("```"):].strip()
    if cleaned.endswith("```"):
        cleaned = cleaned[:-len("```")].strip()
    return json.loads(cleaned)
# ---------------------------------------------------------
# AI 결과를 일정한 형식으로 반환하는 함수
# ---------------------------------------------------------
def generate_travel_recommendation(user_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    사용자의 입력 폼 정보(지역, 시간, 비용, 관심사)를 받아 AI 여행 장소 코스를 추천합니다.
    - ui.py의 user_input 딕셔너리와 그대로 연동됩니다.
    """
    try:
        client, model = get_openrouter_client()
        user_prompt = f"사용자 여행 조건:\n{json.dumps(user_input, ensure_ascii=False, indent=2)}"
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,
            messages=[
                {"role": "system", "content": RECOMMEND_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )
        content = response.choices[0].message.content or "{}"
        parsed_data = _parse_llm_json(content)
        return {
            "status": "success",
            "data": parsed_data
        }
    except Exception as e:
        logger.error(f"[AI Recommendation Error]: {e}")
        return _get_fallback_recommendation(user_input)
def match_travelers(user_a: Dict[str, Any], user_b: Dict[str, Any]) -> Dict[str, Any]:
    """
    두 여행객의 성향과 일정을 비교하여 AI 매칭 결과를 반환합니다.
    """
    try:
        client, model = get_openrouter_client()
        user_prompt = (
            f"내 정보:\n{json.dumps(user_a, ensure_ascii=False, indent=2)}\n\n"
            f"상대 여행객 정보:\n{json.dumps(user_b, ensure_ascii=False, indent=2)}"
        )
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,
            messages=[
                {"role": "system", "content": MATCHING_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )
        content = response.choices[0].message.content or "{}"
        parsed_data = _parse_llm_json(content)
        return {
            "status": "success",
            "data": parsed_data
        }
    except Exception as e:
        logger.error(f"[AI Matching Error]: {e}")
        return _get_fallback_matching()

def choose_places_from_csv(conditions, candidates):
    """CSV의 실제 장소 중 AI가 추천할 장소를 선정한다."""
    if not candidates:
        return []

    if not (os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")):
        return []

    options = [
        {
            "place_id": p["place_id"],
            "name": p["name"],
            "category": p["category"],
            "tags": p["tags"],
        }
        for p in candidates[:30]
    ]

    try:
        client, model = get_openrouter_client()
        response = client.chat.completions.create(
            model=model,
            temperature=0.2,
            max_tokens=800,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "실제 제공된 장소 중에서만 2~4곳을 추천해. "
                        "사용자 취향과 동행인, 피하고 싶은 조건(avoid)을 고려해. "
                        "조건을 확실히 만족하지 못하면 추천에서 제외해. "
                        "CSV에 없는 영업시간이나 가격 정보는 지어내지 마. "
                        "JSON만 반환해. 형식: "
                        '{"recommendations":['
                        '{"place_id":"장소ID","reason":"추천 이유"}]}'
                        "반드시 제공된 place_id만 사용해."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"conditions": conditions, "places": options},
                        ensure_ascii=False
                    ),
                },
            ],
        )

        result = _parse_llm_json(response.choices[0].message.content or "{}")
        valid = {p["place_id"] for p in options}
        selected = []
        seen = set()

        for item in result.get("recommendations", []):
            if not isinstance(item, dict):
                continue
            pid = item.get("place_id")
            if pid in valid and pid not in seen:
                selected.append({
                    "place_id": pid,
                    "reason": str(item.get("reason", ""))
                })
                seen.add(pid)
            if len(selected) == 4:
                break

        return selected

    except Exception:
        logger.exception("AI 장소 선정 실패")
        return []


# ---------------------------------------------------------
# 예시 입력 1~3개로 AI 응답 테스트 (직접 실행용 코드)
# ---------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print(" 🚀 OpenRouter AI 서비스 기능 테스트 시작")
    print("=" * 60)
    # 예시 입력 1: 성수 지역, 오후 4시간 코스, 1곳당 예산 25,000원
    test_input_1 = {
        "region": "성수",
        "date": "2026-11-14",
        "start_time": "13:00",
        "end_time": "17:00",
        "max_price": 25000,
        "categories": ["카페", "전시", "팝업스토어"]
    }
    print("\n[테스트 1] 성수동 감성 코스 추천 (장소 1곳당 25,000원 이하)")
    res1 = generate_travel_recommendation(test_input_1)
    print(json.dumps(res1, indent=2, ensure_ascii=False))
    # 예시 입력 2: 홍대 지역, 저녁 시간대, 저예산 맛집/소품샵
    test_input_2 = {
        "region": "홍대",
        "date": "2026-11-15",
        "start_time": "18:00",
        "end_time": "21:30",
        "max_price": 15000,
        "categories": ["음식점", "소품샵"]
    }
    print("\n[테스트 2] 홍대 저녁 가성비 코스 추천 (장소 1곳당 15,000원 이하)")
    res2 = generate_travel_recommendation(test_input_2)
    print(json.dumps(res2, indent=2, ensure_ascii=False))
    # 예시 입력 3: 성수 지역에서 시간이 겹치는 여행객 간 매칭 분석
    my_profile = {
        "traveler_id": "me",
        "region": "성수",
        "overlap": "14:00~16:30",
        "interests": ["사진 촬영", "디저트 카페", "전시회 관람"]
    }
    peer_traveler = {
        "traveler_id": "traveler_03",
        "region": "성수",
        "overlap": "14:00~16:30",
        "interests": ["디저트 카페", "팝업스토어 투어", "사진"]
    }
    print("\n[테스트 3] 성수동 동행 여행객 AI 매칭 분석")
    res3 = match_travelers(my_profile, peer_traveler)
    print(json.dumps(res3, indent=2, ensure_ascii=False))
    print("\n" + "=" * 60)
    print(" ✅ 모든 테스트 완료! ")
    print("=" * 60)
