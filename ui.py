"""프론트엔드 담당 파일 (Streamlit).

실행 방법 (저장소 폴더에서):  streamlit run ui.py

화면 구성: 입력 폼 → 입력값을 딕셔너리로 묶음 → 추천/매칭 함수 호출 → 결과 카드
"""

import datetime as dt

import streamlit as st

from data_service import get_places_by_region, get_travelers, load_csv

# set_page_config는 다른 st 명령보다 먼저 호출해야 함
st.set_page_config(page_title="여행 추천 (가제)", page_icon="🧳", layout="centered")

TIME_FORMAT = "%Y-%m-%d %H:%M"  # travelers_demo.csv의 시간 형식


# =====================================================================
# 화면 선택지: CSV에서 읽어 온다 → 데이터가 바뀌면 선택지도 자동으로 바뀜
# =====================================================================
def load_options():
    places = load_csv("places.csv")
    travelers = load_csv("travelers_demo.csv")
    regions = sorted({p["region"] for p in places})
    categories = sorted({p["category"] for p in places})
    traveler_dates = sorted({t["start_time"][:10] for t in travelers})
    return regions, categories, traveler_dates


def default_date(traveler_dates):
    # 데모용: 여행객 데이터가 있는 첫 날짜를 기본값으로 (없으면 오늘)
    if traveler_dates:
        return dt.date.fromisoformat(traveler_dates[0])
    return dt.date.today()


# =====================================================================
# 백엔드 연결 지점 ①  장소 추천
# 지금: CSV에서 지역·분류·가격으로 거르는 임시 로직 (AI 연결 전)
#       가격 미확인 장소는 data_service.get_places()와 같은 기준으로 제외
# 나중: ai_service의 함수로 교체 (입력 user_input → 출력 장소 dict 리스트)
# =====================================================================
def get_recommendations(user_input: dict) -> list[dict]:
    results = []
    for place in get_places_by_region(user_input["region"]):
        if place["category"] not in user_input["categories"]:
            continue
        price = place["price_krw"].strip()
        if not price:
            continue
        if int(price) <= user_input["max_price"]:
            results.append(place)
    return results


# =====================================================================
# 백엔드 연결 지점 ②  여행객 매칭
# 조건: 같은 지역 + 매칭 동의(get_travelers가 처리) + 시간대가 겹침
# =====================================================================
def get_matched_travelers(user_input: dict) -> list[dict]:
    my_start = dt.datetime.strptime(f"{user_input['date']} {user_input['start_time']}", TIME_FORMAT)
    my_end = dt.datetime.strptime(f"{user_input['date']} {user_input['end_time']}", TIME_FORMAT)

    matched = []
    for traveler in get_travelers(user_input["region"]):
        t_start = dt.datetime.strptime(traveler["start_time"], TIME_FORMAT)
        t_end = dt.datetime.strptime(traveler["end_time"], TIME_FORMAT)
        # 두 시간대가 겹치는 조건: 상대가 내 끝 시간 전에 시작하고, 내가 상대 끝 시간 전에 시작
        if t_start < my_end and my_start < t_end:
            overlap = f"{max(my_start, t_start):%H:%M}~{min(my_end, t_end):%H:%M}"
            matched.append({**traveler, "overlap": overlap})
    return matched


def price_text(place: dict) -> str:
    price = place["price_krw"].strip()
    if not price:
        return "가격 미확인"
    if int(price) == 0:
        return "무료"
    return f"{int(price):,}원"


# =====================================================================
# 화면: 제목
# =====================================================================
st.title("🧳 여행 추천 & 동행 찾기 (가제)")
st.caption("지역·시간·비용·관심 분야를 고르면 장소를 추천하고, 시간이 겹치는 여행객을 보여줍니다.")

regions, categories, traveler_dates = load_options()

# =====================================================================
# 화면: 입력 폼
# st.form 안의 위젯은 값을 바꿔도 다시 실행되지 않고, 버튼을 누를 때 한 번에 제출됨
# =====================================================================
with st.form("trip_form"):
    col1, col2 = st.columns(2)
    with col1:
        region = st.selectbox("지역", regions)
    with col2:
        date = st.date_input("날짜", value=default_date(traveler_dates))
    time_range = st.slider(
        "시간대",
        min_value=dt.time(6, 0),
        max_value=dt.time(23, 0),
        value=(dt.time(13, 0), dt.time(17, 0)),
        step=dt.timedelta(minutes=30),
    )
    max_price = st.number_input("장소 1곳당 최대 비용 (원)", min_value=0, value=20000, step=5000)
    selected_categories = st.multiselect("관심 분야", categories, default=categories)
    submitted = st.form_submit_button("추천 받기", type="primary")

# =====================================================================
# 제출 시: 입력값 → 딕셔너리 → 추천/매칭 함수 → session_state에 저장
# (session_state에 저장해야 "동행 요청" 버튼 등으로 다시 실행돼도 결과가 남음)
# =====================================================================
if submitted:
    start, end = time_range
    if start >= end:
        st.warning("끝나는 시간이 시작 시간보다 늦어야 해요.")
    elif not selected_categories:
        st.warning("관심 분야를 하나 이상 골라 주세요.")
    else:
        user_input = {
            "region": region,
            "date": date.isoformat(),  # "2026-11-14" 형태의 문자열
            "start_time": start.strftime("%H:%M"),
            "end_time": end.strftime("%H:%M"),
            "max_price": int(max_price),
            "categories": selected_categories,
        }
        st.session_state["user_input"] = user_input
        st.session_state["places"] = get_recommendations(user_input)
        st.session_state["travelers"] = get_matched_travelers(user_input)

# =====================================================================
# 화면: 결과
# =====================================================================
if "user_input" in st.session_state:
    with st.expander("백엔드로 넘기는 값 (개발 확인용)"):
        st.json(st.session_state["user_input"])

    places = st.session_state["places"]
    travelers = st.session_state["travelers"]
    tab_places, tab_travelers = st.tabs(
        [f"📍 추천 장소 ({len(places)})", f"🤝 함께할 여행객 ({len(travelers)})"]
    )

    with tab_places:
        if not places:
            st.info("조건에 맞는 장소가 없어요. 비용이나 관심 분야를 바꿔 보세요.")
        cols = st.columns(2)
        for i, place in enumerate(places):
            with cols[i % 2]:
                with st.container(border=True):
                    st.markdown(f"**{place['name']}**")
                    info = f"{place['category']} · {price_text(place)}"
                    if place["duration_min"].strip():
                        info += f" · 약 {place['duration_min']}분"
                    st.write(info)
                    st.caption(place["address"])
                    if place["tags"].strip():
                        st.caption(" ".join(f"#{tag}" for tag in place["tags"].split("|")))
                    if place["source_url"].strip():
                        st.markdown(f"[출처 보기]({place['source_url']})")

    with tab_travelers:
        if not travelers:
            st.info("이 지역·시간대에 매칭 가능한 여행객이 없어요.")
        for traveler in travelers:
            with st.container(border=True):
                label = f"여행객 {traveler['traveler_id']}"
                if traveler.get("is_demo", "").lower() == "true":
                    label += " (데모)"
                st.markdown(f"**{label}**")
                st.write(f"겹치는 시간: {traveler['overlap']}")
                st.caption("관심사: " + ", ".join(traveler["interests"].split("|")))
                if st.button("동행 요청", key=f"match_{traveler['traveler_id']}"):
                    st.toast(f"{traveler['traveler_id']}에게 동행 요청을 보냈어요 (임시 기능)")
