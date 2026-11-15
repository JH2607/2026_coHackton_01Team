"""
4번 담당 모듈: AI 툴 호출 + 키워드 확장·축소 (ai_chat_agent.py)
- 기존 팀원들의 파일을 수정하지 않고 독립적으로 테스트 및 연동 가능하도록 분리된 모듈
"""
import os
import json
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv
from openai import OpenAI

import db_tools

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CHAT_SYSTEM_PROMPT = """
너는 대한민국 로컬 여행 코스 추천 AI 에이전트다.
사용자의 질문을 분석하여 제공된 도구(`search_places`, `get_place_detail`)를 호출해 실제 DB에서 장소를 찾아야 한다.

[핵심 행동 규칙]
1. 키워드 확장: 질문의 상황/분위기 키워드를 DB 태그나 카테고리로 확장해서 검색해라.
   - 예: "비 오는 날 데이트" -> tags=["실내", "분위기"], categories=["카페", "전시"], companion="연인"
   - 예: "혼자 조용히" -> companion="혼자", tags=["조용한곳", "휴식"]
2. 반복 호출 (조건 추가 및 완화):
   - 1차 검색 결과가 0~1개로 너무 적으면, 태그(tags)나 동행(companion) 조건을 빼고 지역(region)과 카테고리만으로 조건을 완화해 `search_places`를 다시 호출해라.
   - 1차 검색 결과가 너무 많고 포괄적이면, 태그 조건을 추가해 다시 호출해라.
3. 절대 규칙 (환각 방지):
   - 최종 응답의 `places` 목록에는 반드시 도구 실행 결과로 받은 실제 `place_id`만 포함해라. 없는 ID를 지어내지 마라.
4. 출력 형식:
   - 모든 도구 탐색이 끝나면 마크다운 코드블록(```json) 없이 순수 JSON 문자열만 출력해라.

[최종 JSON 출력 형식]
{
  "reply": "사용자에게 건네는 친절하고 자연스러운 추천 멘트",
  "places": [
    {
      "place_id": "실제_DB_ID",
      "reason": "핵심 키워드 2~3개 요약 (예: 조용함 · 창가석 · 디저트)"
    }
  ]
}
"""

def _get_client() -> tuple[OpenAI, str]:
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.getenv("LLM_MODEL", "google/gemini-2.0-flash-001")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY가 .env에 설정되어 있지 않습니다.")
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        default_headers={
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "2026_coHackton_01Team_Agent4"
        }
    )
    return client, model

def _parse_json(raw_text: str) -> Dict[str, Any]:
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json"):].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[len("```"):].strip()
    if cleaned.endswith("```"):
        cleaned = cleaned[:-len("```")].strip()
    return json.loads(cleaned)

def _fallback_search(question: str, error_msg: str = "") -> Dict[str, Any]:
    """API 오류 또는 툴 호출 실패 시 안전하게 DB 기본 검색으로 대체"""
    region = "홍대" if any(w in question for w in ["홍대", "연남", "합정"]) else "성수"
    res = db_tools.search_places(region=region, limit=4)
    places = [
        {"place_id": p["place_id"], "reason": " · ".join(p.get("tags", [])[:3]) or "인기 장소"}
        for p in res.get("places", [])
    ]
    return {
        "reply": f"조건에 맞는 {region} 추천 장소입니다. {error_msg}".strip(),
        "places": places,
        "tool_calls": [{"name": "search_places (fallback)", "arguments": {"region": region}, "count": len(places)}]
    }

def chat_recommend(question: str, history: List[Dict[str, str]] | None = None) -> Dict[str, Any]:
    """
    [최종 결과 함수] 질문 문장 -> Tool Calling 반복(확장/축소) -> 검증된 추천 목록 반환
    """
    history = history or []
    tool_calls_log = []
    
    try:
        client, model = _get_client()
        messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
        for msg in history[-4:]:  # 최근 대화 4개만 유지하여 토큰 절약
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": question})

        # 최대 3회까지 LLM이 스스로 판단하여 툴을 반복 호출(조건 확장/축소)할 수 있도록 루프 구성
        final_content = "{}"
        for step in range(3):
            response = client.chat.completions.create(
                model=model,
                temperature=0.2,
                messages=messages,
                tools=db_tools.TOOL_SCHEMAS,
                tool_choice="auto",
                timeout=12
            )
            msg = response.choices[0].message

            # LLM이 툴 호출을 요청한 경우
            if msg.tool_calls:
                messages.append(msg)  # 어시스턴트의 tool_call 메시지 기록
                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    fn_args_str = tc.function.arguments
                    
                    # 3번 팀원의 dispatch_tool_call 실행
                    tool_result = db_tools.dispatch_tool_call(fn_name, fn_args_str)
                    
                    parsed_args = json.loads(fn_args_str) if isinstance(fn_args_str, str) else fn_args_str
                    count = tool_result.get("count", 1 if tool_result.get("found") else 0)
                    tool_calls_log.append({
                        "name": fn_name,
                        "arguments": parsed_args,
                        "count": count
                    })

                    # 툴 실행 결과를 다시 LLM에게 전달 (결과가 0개면 LLM이 다음 루프에서 조건을 완화함)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(tool_result, ensure_ascii=False)
                    })
            else:
                # 툴 호출이 더 이상 없으면 최종 답변 생성 완료
                final_content = msg.content or "{}"
                break

        parsed = _parse_json(final_content)

        # DB에 실제 존재하는 place_id만 필터링 (없는 ID 제거)
        valid_ids = {p["place_id"] for p in db_tools.load_places()}
        verified_places = []
        seen = set()
        for item in parsed.get("places", []):
            pid = str(item.get("place_id", "")).strip()
            if pid in valid_ids and pid not in seen:
                seen.add(pid)
                verified_places.append({
                    "place_id": pid,
                    "reason": str(item.get("reason", "추천 장소")).strip()
                })

        # 만약 LLM이 유효한 ID를 하나도 못 골랐다면 로그에 남은 마지막 검색 결과에서 보충
        if not verified_places:
            return _fallback_search(question)

        return {
            "reply": str(parsed.get("reply", "맞춤 장소를 찾았어요!")).strip(),
            "places": verified_places,
            "tool_calls": tool_calls_log
        }

    except Exception as e:
        logger.error(f"[chat_recommend 오류]: {e}")
        return _fallback_search(question, f"(안전 모드 전환: {type(e).__name__})")


# =========================================================
# 단독 실행 테스트 (터미널에서 바로 실행해서 확인용)
# =========================================================
if __name__ == "__main__":
    test_questions = [
        "비 오는 날 성수에서 연인이랑 실내 데이트할 곳 추천해줘",
        "홍대에서 혼자 조용히 책 읽거나 쉴 수 있는 카페 있을까?",
        "성수에서 1인당 15000원 이하로 갈 만한 곳 알려줘"
    ]
    
    print("🚀 4번 AI 툴 호출 & 키워드 확장/축소 테스트 시작...\n")
    for q in test_questions:
        print("=" * 60)
        print(f"❓ 질문: {q}")
        result = chat_recommend(q)
        print(f"🛠️ 툴 호출 기록 ({len(result['tool_calls'])}회):")
        for tc in result["tool_calls"]:
            print(f"   -> {tc['name']}({tc['arguments']}) => 결과 {tc['count']}건")
        print(f"💬 AI 답변: {result['reply']}")
        print(f"📍 최종 검증된 추천 장소 ({len(result['places'])}곳):")
        for p in result["places"]:
            print(f"   - [{p['place_id']}] {p['reason']}")
        print()