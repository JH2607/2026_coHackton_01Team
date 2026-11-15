"""
AI 기능 담당 파일 (ai_service.py)
담당 분야: 3. AI 추천 만들기 + 4. AI 툴 호출 및 채팅 연동 (chat_recommend)
"""

import os
import json
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv
from openai import OpenAI

import db_tools
import kakao_service

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
        logger.warning("OPENROUTER_API_KEY가 설정되지 않았습니다.")

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

CHAT_SYSTEM_PROMPT = """
너는 대한민국 최고의 맞춤형 로컬 여행 코스 전문 AI 플래너다.
사용자의 질문을 분석하여 제공된 도구(`search_places`)를 호출해 실제 DB에서 장소를 찾아야 한다.

[작성 및 확장·축소 규칙]
1. 키워드 확장: 질문의 목적이나 분위기 키워드(예: "비 오는 날 데이트" → 실내, 분위기, 카페, 전시 등)를 DB 태그에 맞게 유연하게 확장한다.
2. 반복 호출: 결과가 너무 많거나 적으면 조건을 추가하거나 완화하면서 `search_places` 툴을 활용한다.
3. 환각 방지: 최종 출력의 `places`는 반드시 DB에 실제로 존재하는 `place_id`와 추천 이유(reason)만 포함한다. 없는 ID는 절대 금지.
4. 출력 형식: 마크다운 코드블록(```json) 없이 순수 JSON 문자열만 출력한다.

[반환 JSON 규격]
{
  "reply": "사용자에게 건네는 친절한 답변 멘트",
  "places": [
    {
      "place_id": "실제DB에있는ID",
      "reason": "조용함 · 창가석 · 디저트"
    }
  ]
}
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
# 4. 기존 AI 실행 함수 및 ui.py 연동 함수 (유지 필수)
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
        return [
            {"place_id": p.get("place_id", ""), "reason": "인기 추천 장소입니다."}
            for p in candidates[:2]
        ]


# ---------------------------------------------------------
# 5. [4번 기능] AI 툴 호출 + 키워드 확장·축소 및 채팅 연동 (chat_view.py 연동)
# ---------------------------------------------------------
def _smart_keyword_fallback(question: str) -> Dict[str, Any]:
    """API Key가 없거나 오류 시 안전하게 키워드를 분석하여 db_tools로 검색하는 Fallback"""
    region = "홍대" if any(w in question for w in ["홍대", "연남", "합정"]) else "성수"
    
    tags = []
    if any(w in question for w in ["비", "실내", "데이트", "비오는날"]):
        tags.extend(["실내", "분위기"])
    if any(w in question for w in ["조용", "혼자", "휴식"]):
        tags.extend(["조용한곳", "휴식"])
        
    res = db_tools.search_places(region=region, tags=tags if tags else None, limit=4)
    places_found = res.get("places", [])
    
    if len(places_found) < 2:
        try:
            kakao_extra = kakao_service._lookup(question[:10], region, "")
            if kakao_extra.get("lat"):
                places_found.append({
                    "place_id": f"kakao_{abs(hash(kakao_extra['matched_name']))}",
                    "name": kakao_extra["matched_name"],
                    "category": "추천 장소",
                    "address": kakao_extra["matched_address"],
                    "tags": ["외부검색"]
                })
        except Exception:
            pass

    places_out = [
        {"place_id": p["place_id"], "reason": " · ".join(p.get("tags", [])[:3]) or "인기 추천 장소"}
        for p in places_found[:4] if "place_id" in p
    ]
    
    return {
        "reply": f"질문하신 내용을 바탕으로 {region} 지역에서 조건에 맞는 장소를 찾아드렸어요!",
        "places": places_out,
        "tool_calls": [{"name": "search_places (smart_fallback)", "arguments": {"region": region, "tags": tags}, "count": len(places_out)}],
        "mode": "keyword"
    }


def chat_recommend(question: str, history: list[dict]) -> dict:
    """
    [4번 핵심 함수] 질문 문장 → AI 툴 호출(키워드 확장/축소) → 검증된 추천 목록 반환
    chat_view.py와 완벽히 연동됩니다.
    """
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "DUMMY_KEY_FOR_LOCAL_TEST":
        return _smart_keyword_fallback(question)

    try:
        client, model = get_openrouter_client()
        messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
        for h in (history or []):
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": question})

        tool_calls_history = []
        search_result = {"count": 0, "places": []}
        
        # 최대 3회까지 툴 반복 호출 (결과가 적거나 많을 때 조건 완화/추가)
        final_content = "{}"
        for _ in range(3):
            response = client.chat.completions.create(
                model=model,
                temperature=0.3,
                messages=messages,
                tools=db_tools.TOOL_SCHEMAS,
                tool_choice="auto",
                timeout=10
            )
            msg = response.choices[0].message
            if msg.tool_calls:
                messages.append(msg)
                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    fn_args = tc.function.arguments
                    tool_output = db_tools.dispatch_tool_call(fn_name, fn_args)
                    
                    parsed_args = json.loads(fn_args) if isinstance(fn_args, str) else fn_args
                    count = tool_output.get("count", len(tool_output.get("places", []))) if isinstance(tool_output, dict) else 0
                    tool_calls_history.append({
                        "name": fn_name,
                        "arguments": parsed_args,
                        "count": count
                    })
                    if isinstance(tool_output, dict):
                        search_result = tool_output
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(tool_output, ensure_ascii=False)
                    })
            else:
                final_content = msg.content or "{}"
                break

        # 결과가 0개면 조건 완화하여 재검색
        if search_result.get("count", 0) == 0:
            region = "홍대" if "홍대" in question else "성수"
            fallback_res = db_tools.search_places(region=region, limit=4)
            search_result = fallback_res
            tool_calls_history.append({
                "name": "search_places",
                "arguments": {"region": region, "note": "결과 부족으로 인한 조건 완화"},
                "count": fallback_res.get("count", 0)
            })

        # 유효한 DB ID만 필터링 (없는 ID 제거)
        valid_ids = {p["place_id"] for p in db_tools.load_places()}
        raw_places = search_result.get("places", [])
        verified_places = []
        seen = set()
        for p in raw_places:
            pid = p.get("place_id")
            if pid in valid_ids and pid not in seen:
                seen.add(pid)
                verified_places.append({
                    "place_id": pid,
                    "reason": " · ".join(p.get("matched_tags", []) or p.get("tags", []))[:30] or "추천 장소"
                })

        parsed = _parse_llm_json(final_content) if final_content != "{}" else {}
        final_places = [
            item for item in parsed.get("places", [])
            if isinstance(item, dict) and item.get("place_id") in valid_ids
        ]

        return {
            "reply": parsed.get("reply", "조건에 맞는 추천 장소입니다."),
            "places": final_places if final_places else verified_places[:4],
            "tool_calls": tool_calls_history,
            "mode": "ai"
        }

    except Exception as e:
        logger.error(f"[AI Service Error]: {e}")
        return _smart_keyword_fallback(question)


if __name__ == "__main__":
    print("✅ ai_service.py 준비 완료!")
            


 
