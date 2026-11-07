"""
AI 기능 담당 파일 (ai_service.py)
담당 분야: 3. AI 추천 만들기 (프롬프트, JSON 출력, 오류 처리)
"""

import os
import json
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv
from openai import OpenAI

# ---------------------------------------------------------
# 1. 환경 변수 로드 및 로깅 설정
# ---------------------------------------------------------
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_openrouter_client() -> tuple[OpenAI, str]:
    """OpenRouter / OpenAI API Client 생성"""
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.getenv("LLM_MODEL", "google/gemini-2.0-flash-001")

    if not api_key:
        logger.warning(" OPENROUTER_API_KEY가 설정되지 않았습니다.")

    client = OpenAI(
        api_key=api_key or "DUMMY_KEY_FOR_LOCAL_TEST",
        base_url=base_url,
        default_headers={
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "2026_coHackton_01Team AI Service"
        }
    )
    return client, model


# ---------------------------------------------------------
# 2. 시스템 프롬프트 정의
# ---------------------------------------------------------
RECOMMEND_SYSTEM_PROMPT = """
너는 대한민국 최고의 맞춤형 로컬 여행 코스 전문 AI 플래너다.
사용자의 여행 지역(region), 여행 시간대(start_time ~ end_time), 1곳당 최대 예산(max_price), 관심 카테고리(categories)를 반영하여 최적의 추천 코스를 작성한다.

[작성 규칙]
1. 사용자가 지정한 지역과 장소 1곳당 최대 예산 한도를 엄격히 준수한다.
2. 장소 목록(places)은 사용자의 동선과 활동 시간을 고려하여 방문하기 적합한 순서로 2~4곳 추천한다.
3. 실제 존재할 가능성이 높은 명확한 상호명을 추천한다.
4. 반드시 아래 지정된 JSON 형식으로만 응답하며, 마크다운 코드블록(```json) 없이 순수 JSON 문자열만 출력한다.

[반환 JSON 규격]
{
  "summary": "추천 코스 전체 요약 한 줄",
  "total_estimated_cost": 25000,
  "places": [
    {
      "name": "장소명",
      "category": "카페 | 전시 | 음식점 | 소품샵 등",
      "price_krw": "15000",
      "duration_min": "60",
      "address": "장소 개략 위치 또는 주소",
      "tags": "해시태그 키워드(|로 구분)",
      "reason": "추천 이유"
    }
  ]
}
"""

MATCHING_SYSTEM_PROMPT = """
너는 여행객 간의 일정 및 취향을 분석하여 최적의 동행 시너지를 제안하는 AI 매칭 전문가다.
반드시 마크다운 코드블록 없이 순수 JSON 문자열만 출력한다.
"""


# ---------------------------------------------------------
# 3. 헬퍼 및 Fallback 함수
# ---------------------------------------------------------
def _parse_llm_json(raw_text: str) -> Dict[str, Any]:
    """LLM 응답에서 마크다운 코드블록 제거 후 안전 파싱"""
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json"):].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[len("```"):].strip()
    if cleaned.endswith("```"):
        cleaned = cleaned[:-len("```")].strip()
    return json.loads(cleaned)


def _get_fallback_recommendation(user_input: Dict[str, Any]) -> Dict[str, Any]:
    """오류 시 반환되는 Fallback 데이터"""
    region = user_input.get("region", "성수")
    return {
        "status": "fallback",
        "message": "AI 서버 연결이 원활하지 않아 기본 추천 코스를 안내해 드립니다.",
        "data": {
            "summary": f"{region} 지역의 인기 추천 명소 코스입니다.",
            "total_estimated_cost": 23000,
            "places": [
                {
                    "name": "대림창고",
                    "category": "카페",
                    "price_krw": "8000",
                    "duration_min": "60",
                    "address": f"서울 {region} 성수이로 78",
                    "tags": "복합문화공간|갤러리카페|핫플",
                    "reason": "지역 방문 시 가장 만족도가 높은 대표 휴식 공간입니다."
                },
                {
                    "name": "어니언 성수",
                    "category": "카페",
                    "price_krw": "15000",
                    "duration_min": "90",
                    "address": f"서울 {region} 아차산로9길 8",
                    "tags": "베이커리|인더스트리얼|디저트",
                    "reason": "유명 베이커리와 함께 넓은 공간에서 편안하게 휴식하기 좋습니다."
                }
            ]
        }
    }


def _get_fallback_matching() -> Dict[str, Any]:
    return {
        "status": "fallback",
        "message": "AI 매칭 분석 중 오류가 발생하여 기본 정보를 반환합니다.",
        "data": {
            "match_score": 80,
            "common_interests": ["카페 탐방", "사진 촬영"],
            "recommended_activity": "인근 카페에서 가볍게 커피 한 잔하며 일정 공유하기",
            "match_reason": "동일 지역 및 겹치는 시간대에 일정이 있는 여행객입니다."
        }
    }


# ---------------------------------------------------------
# 4. 주요 AI 실행 함수
# ---------------------------------------------------------
def generate_travel_recommendation(user_input: Dict[str, Any]) -> Dict[str, Any]:
    """AI 코스 추천 함수"""
    try:
        client, model = get_openrouter_client()
        user_prompt = f"사용자 여행 조건:\n{json.dumps(user_input, ensure_ascii=False, indent=2)}"
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,
            messages=[
                {"role": "system", "content": RECOMMEND_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            timeout=10
        )
        content = response.choices[0].message.content or "{}"
        parsed_data = _parse_llm_json(content)
        return {"status": "success", "data": parsed_data}
    except Exception as e:
        logger.error(f"[AI Recommendation Error]: {e}")
        return _get_fallback_recommendation(user_input)


def match_travelers(user_a: Dict[str, Any], user_b: Dict[str, Any]) -> Dict[str, Any]:
    """동행 AI 매칭 함수"""
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
            ],
            timeout=10
        )
        content = response.choices[0].message.content or "{}"
        parsed_data = _parse_llm_json(content)
        return {"status": "success", "data": parsed_data}
    except Exception as e:
        logger.error(f"[AI Matching Error]: {e}")
        return _get_fallback_matching()


# ---------------------------------------------------------
# 5. ui.py 연동용 핵심 함수 (choose_places_from_csv)
# ---------------------------------------------------------
def choose_places_from_csv(conditions: dict, candidates: list) -> list:
    """CSV의 실제 장소 후보 중 AI가 조건에 맞는 장소를 선정하는 함수 (ui.py 필수 호출)"""
    if not candidates:
        return []

    options = [
        {
            "place_id": p.get("place_id", ""),
            "name": p.get("name", ""),
            "category": p.get("category", ""),
            "tags": p.get("tags", ""),
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
                        "사용자 취향과 조건을 고려해. "
                        "JSON만 반환해. 형식: "
                        '{"recommendations":[{"place_id":"장소ID","reason":"추천 이유"}]}'
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
            timeout=8
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

    except Exception as e:
        logger.warning(f"AI 장소 선정 Fallback 적용: {e}")
        # API 오류/키 누락 시 기본으로 2곳 선정하여 ui.py 멈춤 방지
        return [
            {"place_id": p.get("place_id", ""), "reason": "인기 추천 장소입니다."}
            for p in candidates[:2]
        ]


if __name__ == "__main__":
    print("✅ ai_service.py 준비 완료!")

    

 
