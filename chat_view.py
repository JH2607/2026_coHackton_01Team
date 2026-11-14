"""5번: AI에게 물어보기 (채팅 페이지).

흐름: 사용자가 자유롭게 질문 → ask_ai() → 답변 + 추천 장소 카드(♡) → 오른쪽 'AI 추천에서 찜한 리스트' + 지도

ask_ai()가 4번(AI 툴 호출)과 만나는 연결 지점이에요.
  - ai_service.py에 chat_recommend(question, history) 함수가 생기면 자동으로 그 함수를 씀
  - 아직 없으면(또는 오류가 나면) LLM 없이 db_tools.search_places로 '임시 키워드 검색'을 하고, 화면에 그렇다고 표시함

4번 함수가 돌려줄 형식 (제안)
  chat_recommend(question: str, history: list[dict]) -> dict
    history: 이전 대화 [{"role": "user" | "assistant", "content": "..."}]
    반환 {
      "reply": "사용자에게 보여 줄 답변 문장",
      "places": [{"place_id": "P001", "reason": "조용함 · 창가석 · 디저트"}],   # DB에 있는 ID만, 추천 순서대로
                                                                               # reason은 키워드 2~3개 (카드에 한 줄로 표시)
      "tool_calls": [{"name": "search_places", "arguments": {...}, "count": 12}]  # '어떻게 찾았는지'로 표시
    }
  DB에 없는 place_id는 화면에 나오기 전에 여기서 한 번 더 걸러요.
"""

import streamlit as st

import ai_service
import db_tools
import map_view
import user_store

EXAMPLE_QUESTIONS = [
    "성수에서 친구랑 사진 찍기 좋은 곳 추천해 줘",
    "홍대에서 혼자 조용히 쉴 수 있는 카페 알려 줘",
    "비 오는 날 연인이랑 실내 데이트할 곳 있을까?",
]
MAX_PLACES = 6  # 답변 하나에 보여 줄 장소 수

# ---------------------------------------------------------------------
# 임시 키워드 검색 (4번 AI가 연결되기 전에만 사용) — 질문 속 낱말을 DB 조건으로 바꿔서 검색
# ---------------------------------------------------------------------
REGION_WORDS = {"성수": "성수", "서울숲": "성수", "뚝섬": "성수", "홍대": "홍대", "연남": "홍대", "합정": "홍대"}
COMPANION_WORDS = {"혼자": "혼자", "친구": "친구", "연인": "연인", "애인": "연인", "커플": "연인",
                   "가족": "가족", "부모님": "가족", "아이랑": "가족"}
TAG_WORDS = {"조용": "조용한곳", "비오": "비오는날", "비 오": "비오는날", "밥": "식사"}


def _vocabulary() -> tuple[set[str], set[str]]:
    places = db_tools.load_places()
    categories = {p["category"] for p in places} | set(db_tools.CATEGORY_ALIASES)
    tags = {t for p in places for field in ("tags", "purpose_tags") for t in db_tools._tokens(p.get(field, ""))}
    return categories, {t for t in tags if len(t) >= 2}


def _read_question(question: str) -> dict:
    text = question.replace(" ", "")
    categories, tags = _vocabulary()
    region = next((r for word, r in REGION_WORDS.items() if word in text), None)
    companion = next((c for word, c in COMPANION_WORDS.items() if word in text), None)
    found_categories = sorted(c for c in categories if c in text)
    found_tags = sorted(t for t in tags if t in text)
    found_tags += [t for word, t in TAG_WORDS.items() if word.replace(" ", "") in text and t not in found_tags]
    return {"region": region, "companion": companion, "categories": found_categories, "tags": found_tags}


def keyword_search(question: str) -> dict:
    """LLM 없이: 질문에서 지역·동행·분류·태그 낱말을 찾아 search_places 호출. 결과가 없으면 조건을 하나씩 뺀다."""
    found = _read_question(question)
    args = {k: v for k, v in found.items() if v}
    if not args:  # 알아들은 조건이 하나도 없으면 아무 장소나 보여 주지 않음
        return {"reply": "질문에서 DB로 찾을 수 있는 조건을 찾지 못했어요. 지금 DB에는 성수 · 홍대 장소가 있어요. "
                         "지역이나 하고 싶은 것(예: 카페, 사진, 산책)을 넣어서 다시 물어봐 주세요.",
                "places": [], "tool_calls": [], "mode": "keyword"}
    tool_calls, dropped = [], []
    result = None
    for drop in (None, "tags", "companion", "categories"):
        if drop:
            if drop not in args:
                continue
            args.pop(drop)
            dropped.append({"tags": "태그", "companion": "동행", "categories": "분류"}[drop])
        result = db_tools.search_places(**args, limit=MAX_PLACES)
        tool_calls.append({"name": "search_places", "arguments": dict(args), "count": result["count"]})
        if result["count"]:
            break

    shown = []
    for place in result["places"]:
        # 추천 이유는 키워드 몇 개만 (카드에 한 줄로 표시): 질문과 맞은 태그 → 없으면 그 장소의 목적 태그
        keywords = place["matched_tags"] or db_tools._tokens(place.get("purpose_tags", ""))
        shown.append({"place_id": place["place_id"], "reason": " · ".join(keywords[:3])})

    understood = [found["region"], found["companion"], *found["categories"], *found["tags"]]
    understood = ", ".join(dict.fromkeys(w for w in understood if w))  # 같은 낱말은 한 번만
    reply = f"질문에서 **{understood}** 조건을 찾아 DB에서 검색했어요. 일치하는 곳 {result['count']}곳 중 {len(shown)}곳을 보여 드려요."
    if dropped:
        reply += f" (딱 맞는 곳이 없어서 {', '.join(dropped)} 조건을 빼고 다시 찾았어요.)"
    if not shown:
        reply = "DB에서 맞는 장소를 찾지 못했어요. 지역(성수·홍대)이나 하고 싶은 것을 넣어서 다시 물어봐 주세요."
    return {"reply": reply, "places": shown, "tool_calls": tool_calls, "mode": "keyword"}


# ---------------------------------------------------------------------
# 4번 연결 지점
# ---------------------------------------------------------------------
def ai_connected() -> bool:
    return callable(getattr(ai_service, "chat_recommend", None))


def _clean(raw: dict, places_by_id: dict) -> dict:
    """AI 결과를 화면용으로 정리: DB에 없는 ID · 중복 제거, 개수 제한."""
    places, seen = [], set()
    for item in (raw or {}).get("places", []):
        place_id = str(item.get("place_id", "")).strip()
        if place_id in places_by_id and place_id not in seen:
            seen.add(place_id)
            places.append({"place_id": place_id, "reason": str(item.get("reason", "")).strip()})
    return {
        "reply": str((raw or {}).get("reply", "")).strip() or "추천 결과예요.",
        "places": places[:MAX_PLACES],
        "tool_calls": list((raw or {}).get("tool_calls", [])),
        "mode": "ai",
    }


def ask_ai(question: str, history: list[dict], places_by_id: dict) -> dict:
    if ai_connected():
        try:
            return _clean(ai_service.chat_recommend(question, history), places_by_id)
        except Exception as exc:  # AI 쪽 오류가 나도 화면은 멈추지 않게, 임시 검색으로 대신함
            result = keyword_search(question)
            result["reply"] = f"AI 응답에 문제가 있어서 키워드 검색으로 대신 찾았어요. ({type(exc).__name__}) " + result["reply"]
            return result
    return keyword_search(question)


# ---------------------------------------------------------------------
# 화면
# ---------------------------------------------------------------------
def _ask_example(question: str):
    st.session_state["chat_pending"] = question


def _new_chat():
    st.session_state["chat_messages"] = []


def _render_answer(index: int, message: dict, user_id: str, places_by_id: dict, picks: list[str], render_card):
    st.markdown(message["content"])
    if message.get("mode") == "keyword":
        st.markdown('<span class="gb-chat-mode">임시 키워드 검색 · AI 연결 전</span>', unsafe_allow_html=True)
    if message.get("tool_calls"):
        with st.expander("어떻게 찾았는지 보기"):
            for call in message["tool_calls"]:
                args = ", ".join(f"{k}={v}" for k, v in call.get("arguments", {}).items()) or "조건 없음"
                count = call.get("count")
                st.markdown(f"- `{call.get('name', '')}`({args})" + (f" → {count}곳" if count is not None else ""))

    pick_no = {place_id: i for i, place_id in enumerate(picks, start=1)}
    cols = st.columns(2, gap="small")
    for i, item in enumerate(message.get("places", [])):
        place = dict(places_by_id[item["place_id"]])
        place["ai_reason"] = item.get("reason", "")
        place["reason_badge"] = "AI PICK" if message.get("mode") == "ai" else "DB 검색"
        with cols[i % 2]:
            render_card(place, pick_no.get(place["place_id"]), f"chat{index}",
                        user_store.toggle_ai_pick, (user_id,))


def render_chat_page(user_id: str, places_by_id: dict, render_card, map_places_for):
    """render_card: ui.render_place_card / map_places_for: ui.map_places_for (순환 import를 피하려고 받아서 씀)."""
    messages = st.session_state.setdefault("chat_messages", [])

    st.markdown('<div class="gb-chat-title">AI에게 물어보기</div>'
                '<div class="gb-chat-sub">원하는 여행을 문장으로 적으면, 김밥 DB에 있는 실제 장소 중에서 골라 드려요.</div>',
                unsafe_allow_html=True)
    if not ai_connected():
        st.markdown('<div class="gb-chat-notice">지금은 AI 연결 전이라, 질문 속 키워드(지역 · 동행 · 분류 · 태그)로 DB를 검색해요.</div>',
                    unsafe_allow_html=True)

    st.markdown('<div class="gb-chat-examples-label">이렇게 물어보세요</div>', unsafe_allow_html=True)
    example_cols = st.columns(3)
    for i, (col, example) in enumerate(zip(example_cols, EXAMPLE_QUESTIONS)):
        col.button(example, key=f"chat_example_{i}", on_click=_ask_example, args=(example,), use_container_width=True)

    chat_col, pick_col = st.columns([3, 2], gap="large")
    with chat_col:
        # 입력창은 예시 질문 바로 아래 (화면 맨 아래에 붙는 방식이 아님: 칸 안에 넣으면 그 자리에 표시됨)
        typed = st.chat_input("어떤 여행을 원하세요? 자유롭게 적어 주세요", key="chat_box")
        question = (typed or st.session_state.pop("chat_pending", "") or "").strip()
        if question:
            history = [{"role": m["role"], "content": m["content"]} for m in messages]
            messages.append({"role": "user", "content": question})
            with st.spinner("DB에서 장소를 찾고 있어요..."):
                messages.append({"role": "assistant", **_answer_fields(ask_ai(question, history, places_by_id))})

        picks = user_store.get_ai_picks(user_id)
        if messages:
            st.button("대화 새로 시작", key="chat_new", on_click=_new_chat)
        # 최신 질문·답변이 입력창 바로 아래, 예전 것은 아래로 밀려남
        for start in range(len(messages) - len(messages) % 2 - 2, -1, -2):
            question_msg, answer_msg = messages[start], messages[start + 1]
            with st.chat_message("user"):
                st.markdown(question_msg["content"])
            with st.chat_message("assistant", avatar=":material/explore:"):
                _render_answer(start + 1, answer_msg, user_id, places_by_id, picks, render_card)

    with pick_col, st.container(key="chat_side"):  # 대화를 내려도 오른쪽 지도는 화면에 붙어 있게 (ui_style.py)
        st.markdown('<div class="gb-sub-title">AI 추천에서 찜한 리스트</div>', unsafe_allow_html=True)
        pick_places = map_places_for(picks)
        region = next((places_by_id[p]["region"] for p in picks if p in places_by_id), "")
        if not region:
            latest = next((m for m in reversed(messages) if m["role"] == "assistant" and m.get("places")), None)
            region = places_by_id[latest["places"][0]["place_id"]]["region"] if latest else "성수"
        map_view.render_picks_map(pick_places, region, key="chat", title_text="찜한 순서", stacked=True,
                                  empty_text="아직 찜한 곳이 없어요. 대화에서 추천받은 장소의 ♡를 누르면 "
                                             "여기와 지도에 번호가 생겨요.")
        if picks:
            st.button("찜한 리스트 비우기", key="chat_clear_picks", on_click=user_store.clear_ai_picks, args=(user_id,))


def _answer_fields(result: dict) -> dict:
    return {"content": result["reply"], "places": result["places"],
            "tool_calls": result.get("tool_calls", []), "mode": result.get("mode", "keyword")}
