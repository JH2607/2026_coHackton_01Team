"""프론트엔드 담당 파일 (Streamlit).   실행:  streamlit run ui.py

화면 흐름 (설계도 번호 기준)
  ① 첫 화면 (로그인 전)   : 소개 문구 + 로고 + 기능 소개, 오른쪽 위 [로그인] [회원가입]
  ②③ 회원가입 / 로그인   : 첫 화면 위에 작은 팝업으로 뜸 (st.dialog)
  ④ 메인 화면 (로그인 후) : 목적지 · 날짜 · 체험하고 싶은 것 · 취향 입력 → [확인]
  ⑤ [확인] 후             : 폼 아래에 추천 내용 카드 + 동행에게 공유하기

관련 파일
  ui_style.py   색 · 글꼴 · 로고 · 분류별 그림
  user_store.py 회원 · 찜(하트) · 공유 저장
"""

import datetime as dt
import html

import streamlit as st

import ui_style
import user_store
from data_service import get_places_by_region, load_csv

st.set_page_config(page_title="김밥 · 여행 추천", page_icon="🧭", layout="wide")
st.markdown(ui_style.CSS, unsafe_allow_html=True)

PAGE_SIZE = 6  # 추천 카드를 한 번에 몇 개씩 보여줄지

# 태그로 장소 분위기 판단: 힐링 쪽 태그 vs active 쪽 태그
HEALING_TAGS = {
    "힐링", "휴식", "조용함", "산책", "자연", "공원", "온실", "다도", "전통차", "한옥", "한옥감성",
    "책", "갤러리", "전시", "카페", "커피", "핸드드립", "로스터리", "스페셜티커피", "바다감성",
    "디저트", "브런치", "베이커리", "동물카페", "반려동물", "서울숲",
}
ACTIVE_TAGS = {
    "액티비티", "운동", "헬스", "체험", "원데이클래스", "공방", "공예", "도자기", "드로잉", "댄스",
    "게임", "공연", "버스킹", "거리문화", "쇼핑", "팝업", "플리마켓", "시장", "전통시장", "길거리음식",
    "심야", "야간", "KPOP", "아이돌", "미디어아트", "포토존", "패션", "메이크업", "퍼스널컬러",
    "벽화", "그래피티", "거리산책",
}


def esc(text) -> str:
    """CSV 글자를 HTML에 넣기 전에 안전하게 바꾼다 (<, > 같은 문자가 화면을 깨뜨리지 않도록)."""
    return html.escape(str(text), quote=True)


def flash(message: str) -> None:
    """화면이 새로고침된 다음에 보여줄 알림을 예약한다."""
    st.session_state["flash"] = message


# =====================================================================
# 추천 로직 (백엔드 연결 지점)
# 지금: CSV에서 목적지 · 분류로 거르고, 힐링/active 취향에 가까운 순서로 정렬
# 나중: AI 함수로 바꾸려면 이 함수의 안쪽만 바꾸면 됨 (입력 trip dict → 장소 dict 리스트)
# =====================================================================
def place_active_ratio(place: dict) -> float:
    """장소가 active 쪽에 얼마나 가까운지 0.0(힐링) ~ 1.0(active). 판단할 태그가 없으면 0.5."""
    tags = set(place["tags"].split("|"))
    healing = len(tags & HEALING_TAGS)
    active = len(tags & ACTIVE_TAGS)
    if healing + active == 0:
        return 0.5
    return active / (healing + active)


def get_recommendations(trip: dict) -> list[dict]:
    wanted = set(trip["categories"])
    target = trip["active"] / 100
    results = []
    for place in get_places_by_region(trip["region"]):
        if wanted and place["category"] not in wanted:
            continue
        fit = 1 - abs(place_active_ratio(place) - target)  # 1에 가까울수록 취향에 맞음
        results.append({**place, "fit": fit})
    results.sort(key=lambda p: (-p["fit"], p["name"]))
    return results


def cost_html(place: dict) -> str:
    price = place["price_krw"].strip()
    if not price:
        return '<span class="gb-cost unknown">1인 비용 · 가격 미확인</span>'
    if int(price) == 0:
        return '<span class="gb-cost">1인 비용 · 무료</span>'
    return f'<span class="gb-cost">1인 비용 · 약 {int(price):,}원</span>'


def one_line(place: dict) -> str:
    """한 줄 소개: 태그 3개 + 머무는 시간."""
    tags = [t for t in place["tags"].split("|") if t][:3]
    text = " ".join(f"#{t}" for t in tags)
    if place["duration_min"].strip():
        text += f" · 약 {place['duration_min']}분"
    return text


# =====================================================================
# ②③ 팝업: 회원가입 / 로그인 / 공유
# =====================================================================
@st.dialog("회원가입", width="small")
def signup_dialog():
    user_id = st.text_input("아이디 (username)", placeholder="영문·숫자·_ 3~20자")
    password = st.text_input("비밀번호 (password)", type="password", placeholder="4자 이상")
    agreed = st.checkbox("[필수] 약관 (개인정보 수집·이용) 에 동의합니다")
    if st.button("회원가입", type="primary", use_container_width=True):
        error = user_store.create_user(user_id, password, agreed)
        if error:
            st.error(error)
        else:
            flash("회원가입이 완료됐어요! 로그인해 주세요.")
            st.rerun()


@st.dialog("로그인", width="small")
def login_dialog():
    user_id = st.text_input("아이디 (username)")
    password = st.text_input("비밀번호 (password)", type="password")
    st.markdown("김밥에 오신 것을 환영합니다 🎉")
    if st.button("로그인", type="primary", use_container_width=True):
        if user_store.check_login(user_id, password):
            st.session_state["user"] = user_id.strip()
            flash(f"{user_id.strip()}님, 반가워요!")
            st.rerun()  # 페이지 새로고침 → 메인 화면(④)으로
        else:
            st.error("아이디 또는 비밀번호가 맞지 않아요.")


@st.dialog("본 파일 공유..", width="small")
def share_dialog(trip: dict, place_ids: list[str]):
    st.caption(f"지금 보고 있는 추천 {len(place_ids)}곳을 함께 여행할 동행에게 보내요.")
    to_user = st.text_input("공유할 사용자 ID")
    if st.button("공유", type="primary", use_container_width=True):
        error = user_store.share_trip(st.session_state["user"], to_user, trip, place_ids)
        if error:
            st.error(error)
        else:
            flash(f"{to_user.strip()}님에게 공유했어요!")
            st.rerun()


# =====================================================================
# ① 첫 화면 (로그인 전)
# =====================================================================
PREVIEW_RECOMMEND = f"""
<div class="gb-preview" aria-hidden="true">
  <div class="gb-pv-row">목적지 <div class="gb-pv-field"></div></div>
  <div class="gb-pv-row">날짜 <div class="gb-pv-field"></div> – <div class="gb-pv-field"></div></div>
  <div class="gb-pv-row">취향 &nbsp;힐링 <div class="gb-pv-field" style="height:6px"></div> active</div>
  <div class="gb-pv-cards">
    <div class="gb-pv-card"><img src="{ui_style.category_image_uri('카페')}" alt=""><div>카페 ♡</div></div>
    <div class="gb-pv-card"><img src="{ui_style.category_image_uri('문화체험')}" alt=""><div>문화체험 ♡</div></div>
  </div>
</div>"""

PREVIEW_SHARE = """
<div class="gb-preview" aria-hidden="true">
  <div style="font-family:'Jua',sans-serif;font-size:1.2rem">본 파일 공유..</div>
  <div class="gb-pv-row">공유할 사용자 ID <div class="gb-pv-field"></div></div>
  <div style="text-align:center"><span class="gb-pv-btn">공유</span></div>
  <div class="gb-pv-row" style="margin-top:16px">📨 친구가 공유한 성수 여행 · 3곳</div>
</div>"""


def render_landing():
    top = st.columns([6, 1.2, 1.4], vertical_alignment="center")
    top[0].markdown(
        '<div class="gb-intro">취향대로 골라 한 줄로 말아 주는 여행 추천 서비스, <b>김밥</b></div>',
        unsafe_allow_html=True,
    )
    if top[1].button("로그인", use_container_width=True):
        login_dialog()
    if top[2].button("회원가입", type="primary", use_container_width=True):
        signup_dialog()

    st.markdown(ui_style.logo_html("big"), unsafe_allow_html=True)
    st.markdown(
        '<div class="gb-scroll">scroll down to see more<span class="gb-arrow">⌄</span></div>',
        unsafe_allow_html=True,
    )

    # 기능 1: 왼쪽 그림 / 오른쪽 설명
    row1 = st.columns(2, gap="large", vertical_alignment="center")
    row1[0].markdown(PREVIEW_RECOMMEND, unsafe_allow_html=True)
    row1[1].markdown(
        '<div class="gb-feature-title">기능 1 · 맞춤 장소 추천</div>'
        '<div class="gb-feature-text">목적지, 날짜, 꼭 해 보고 싶은 것, 힐링과 active 사이의 취향을 고르면 '
        '성수·홍대의 음식점, 카페, 문화체험 등을 추천해 드려요. '
        '카드의 그림을 누르면 원래 안내 페이지로 이동하고, 하트로 마음에 드는 곳을 찜할 수 있어요.</div>',
        unsafe_allow_html=True,
    )
    st.write("")
    # 기능 2: 왼쪽 설명 / 오른쪽 그림
    row2 = st.columns(2, gap="large", vertical_alignment="center")
    row2[0].markdown(
        '<div class="gb-feature-title">기능 2 · 동행과 공유</div>'
        '<div class="gb-feature-text">함께 여행하는 친구의 아이디를 입력하면 지금 보고 있는 추천을 그대로 보내요. '
        '친구가 로그인하면 공유받은 여행을 바로 확인할 수 있어요.</div>',
        unsafe_allow_html=True,
    )
    row2[1].markdown(PREVIEW_SHARE, unsafe_allow_html=True)

    st.markdown('<div class="gb-footer">TEAM GIMBAP · 2026 연합 해커톤</div>', unsafe_allow_html=True)


# =====================================================================
# ④⑤ 메인 화면 (로그인 후)
# =====================================================================
def render_header(user_id: str):
    cols = st.columns([1.1, 5, 1.9, 0.9], vertical_alignment="center")
    cols[0].markdown(ui_style.logo_html("small"), unsafe_allow_html=True)
    cols[1].markdown(
        '<div class="gb-tagline"><span>사용자의 예산, 여행 취향, 일정에 맞는</span><br>'
        '<span>여가활동 · 맛집 · 랜드마크 · 문화체험 · 교류</span> 서비스입니다.</div>',
        unsafe_allow_html=True,
    )
    with cols[2]:
        st.markdown(f'<div class="gb-userid" title="{esc(user_id)}">{esc(user_id)}</div>', unsafe_allow_html=True)
        if st.button("로그아웃", key="logout", use_container_width=True):
            st.session_state.clear()
            flash("로그아웃했어요.")
            st.rerun()
    cols[3].markdown(
        f'<div class="gb-avatar" role="img" aria-label="프로필 사진 자리">{esc(user_id[:1].upper())}</div>',
        unsafe_allow_html=True,
    )


def render_trip_form(regions: list[str], categories: list[str]):
    st.write("")
    left, center, right = st.columns([1, 6, 1])
    with center, st.form("trip_form"):
        region = st.selectbox("목적지", regions)

        today = dt.date.today()
        date_cols = st.columns([5, 0.5, 5], vertical_alignment="bottom")
        start = date_cols[0].date_input("날짜 (시작)", value=today, min_value=today)
        date_cols[1].markdown("<div style='text-align:center;padding-bottom:0.45rem;font-size:1.3rem'>~</div>",
                              unsafe_allow_html=True)
        end = date_cols[2].date_input("날짜 (끝)", value=today + dt.timedelta(days=2), min_value=today)

        picked = st.multiselect("꼭 체험해 보고 싶은 것", categories, placeholder="선택하지 않으면 전체에서 추천해요")

        active = st.slider("이번 여행의 취향", min_value=0, max_value=100, value=50, step=10, format="active %d%%",
                           help="왼쪽으로 갈수록 힐링, 오른쪽으로 갈수록 active 한 장소를 먼저 보여줘요.")
        st.markdown('<div class="gb-slider-ends"><span>← 힐링</span><span>active →</span></div>',
                    unsafe_allow_html=True)

        submitted = st.form_submit_button("확인", type="primary", use_container_width=True)

    if submitted:
        if end < start:
            st.warning("끝나는 날짜가 시작 날짜보다 빠를 수 없어요.")
            return
        st.session_state["trip"] = {
            "region": region,
            "start_date": start.isoformat(),  # 예: "2026-11-14"
            "end_date": end.isoformat(),
            "categories": picked,             # 비어 있으면 전체
            "active": active,                 # 0 = 완전 힐링, 100 = 완전 active
        }
        st.session_state["shown"] = PAGE_SIZE


def toggle_heart(user_id: str, place_id: str):
    user_store.toggle_favorite(user_id, place_id)


def render_place_card(place: dict, favorites: set[str], user_id: str, key_prefix: str):
    with st.container(border=True):
        url = esc(place["source_url"])
        img = ui_style.category_image_uri(place["category"])
        st.markdown(
            f'<div class="gb-card-img"><a href="{url}" target="_blank" rel="noopener noreferrer" '
            f'title="원래 페이지 열기"><img src="{img}" alt="{esc(place["name"])} 원래 페이지 열기"></a></div>',
            unsafe_allow_html=True,
        )
        name_col, heart_col = st.columns([5, 1], vertical_alignment="center")
        name_col.markdown(
            f'<div class="gb-card-name">{esc(place["name"])} <small>({esc(place["category"])})</small></div>',
            unsafe_allow_html=True,
        )
        liked = place["place_id"] in favorites
        heart_col.button(
            "❤️" if liked else "♡",
            key=f"{key_prefix}_heart_{place['place_id']}",
            help="찜 취소" if liked else "찜하기",
            on_click=toggle_heart,
            args=(user_id, place["place_id"]),
        )
        st.markdown(f'<div class="gb-card-line">{esc(one_line(place))}</div>{cost_html(place)}',
                    unsafe_allow_html=True)


def show_more():
    st.session_state["shown"] += PAGE_SIZE


def render_results(user_id: str):
    trip = st.session_state["trip"]
    places = get_recommendations(trip)
    shown = places[: st.session_state.get("shown", PAGE_SIZE)]

    st.write("")
    head = st.columns([6, 2.2, 0.8], vertical_alignment="center")
    head[0].markdown('<div class="gb-section-title">추천 내용</div>', unsafe_allow_html=True)
    head[1].markdown('<div class="gb-share-label">Share the file with</div>', unsafe_allow_html=True)
    if head[2].button(":material/group:", key="share_btn", help="동행에게 공유하기"):
        share_dialog(trip, [p["place_id"] for p in shown])

    picked = ", ".join(trip["categories"]) if trip["categories"] else "전체 분류"
    chips = [
        trip["region"],
        f"{trip['start_date']} ~ {trip['end_date']}",
        f"힐링 {100 - trip['active']}% — active {trip['active']}%",
        picked,
    ]
    st.markdown('<div class="gb-chips">' + "".join(f'<span class="gb-chip">{esc(c)}</span>' for c in chips) + "</div>",
                unsafe_allow_html=True)

    if not places:
        st.info("조건에 맞는 장소가 없어요. 꼭 체험해 보고 싶은 것을 바꿔 보세요.")
        return

    favorites = user_store.get_favorites(user_id)
    cols = st.columns(2, gap="medium")
    for i, place in enumerate(shown):
        with cols[i % 2]:
            render_place_card(place, favorites, user_id, key_prefix="rec")

    if len(shown) < len(places):
        st.button(f"더 보기 ({len(shown)}/{len(places)})", on_click=show_more, use_container_width=True)


def render_shared_inbox(user_id: str, places_by_id: dict):
    shares = user_store.get_shares_for(user_id)
    if not shares:
        return
    with st.expander(f"📨 동행이 공유한 여행 ({len(shares)})"):
        for share in shares:
            trip = share["trip"]
            st.markdown(
                f"**{esc(share['from'])}**님이 보낸 **{esc(trip['region'])}** 여행 "
                f"({esc(trip['start_date'])} ~ {esc(trip['end_date'])})"
            )
            for place_id in share["place_ids"]:
                place = places_by_id.get(place_id)
                if place:
                    st.markdown(f"- [{place['name']}]({place['source_url']}) · {place['category']}")
            st.divider()


def render_main(user_id: str):
    all_places = load_csv("places.csv")
    regions = sorted({p["region"] for p in all_places})
    categories = sorted({p["category"] for p in all_places})

    render_header(user_id)
    render_shared_inbox(user_id, {p["place_id"]: p for p in all_places})
    render_trip_form(regions, categories)
    if "trip" in st.session_state:
        render_results(user_id)


# =====================================================================
# 시작점: 로그인 여부에 따라 ① 또는 ④⑤
# =====================================================================
if "flash" in st.session_state:
    st.toast(st.session_state.pop("flash"))

if "user" in st.session_state:
    render_main(st.session_state["user"])
else:
    render_landing()
