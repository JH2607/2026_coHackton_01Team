"""프론트엔드 담당 파일 (Streamlit).   실행:  streamlit run ui.py

화면 흐름 (설계도 번호 기준)
  ① 첫 화면 (로그인 전)   : 소개 문구 + 로고 + 기능 소개, 오른쪽 위 [로그인] [회원가입]
  ②③ 회원가입 / 로그인   : 첫 화면 위에 작은 팝업으로 뜸 (st.dialog)
  ④ 메인 화면 (로그인 후) : "이번 여행 기획" 폼 (목적지 · 날짜 · 꼭 체험해 보고 싶은 것) → [확인]
  ⑤ [확인] 후             : 추천 내용 카드 (하트로 찜) + 동행에게 공유
                            맨 아래 [사물함에 저장]을 눌러야 사물함에 들어감 (공유 버튼을 눌러도 자동 저장)
  사물함                  : 예전 여행 기획 카드 → [열어 보기] → 사진 · 이름 · 소감 · 공유 · 찜한 리스트 · 추천
                            휴지통: 만든 사람은 파일 삭제(친구 사물함에서도 사라짐), 공유받은 사람은 내 사물함에서만 빼기

관련 파일
  ui_style.py   색 · 글꼴 · 로고 · 분류별 그림
  user_store.py 회원 · 여행 사물함 · 찜 · 공유 저장
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


def esc(text) -> str:
    """CSV · 사용자 입력 글자를 HTML에 넣기 전에 안전하게 바꾼다."""
    return html.escape(str(text), quote=True)


def flash(message: str) -> None:
    """화면이 새로고침된 다음에 보여줄 알림을 예약한다."""
    st.session_state["flash"] = message


def date_range_text(conditions: dict) -> str:
    start = dt.date.fromisoformat(conditions["start_date"])
    end = dt.date.fromisoformat(conditions["end_date"])
    if start == end:
        return f"{start:%Y.%m.%d}"
    return f"{start:%Y.%m.%d} - {end:%m.%d}"


# =====================================================================
# 추천 로직 (백엔드 연결 지점)
# 지금: CSV에서 목적지 · 분류로 거르고, 고른 분류 순서 → 이름 순서로 정렬
# 나중: AI 함수로 바꾸려면 이 함수의 안쪽만 바꾸면 됨 (입력 conditions dict → 장소 dict 리스트)
# =====================================================================
def get_recommendations(conditions: dict) -> list[dict]:
    picked = conditions["categories"]
    order = {category: i for i, category in enumerate(picked)}
    places = [p for p in get_places_by_region(conditions["region"]) if not picked or p["category"] in order]
    places.sort(key=lambda p: (order.get(p["category"], 0), p["category"], p["name"]))
    return places


def cost_html(place: dict) -> str:
    price = place["price_krw"].strip()
    if not price:
        return '<span class="gb-cost unknown">1인 비용 · 가격 미확인</span>'
    if int(price) == 0:
        return '<span class="gb-cost">1인 비용 · 무료</span>'
    return f'<span class="gb-cost">1인 비용 · 약 {int(price):,}원</span>'


COMMON_TAGS = {"사진", "실내", "야외"}  # 어느 장소에나 붙는 태그 → 흐리게, 뒤쪽에


def tags_html(place: dict) -> str:
    """특징 태그 전부를 작은 표시로. 그 장소만의 특징은 진하게 앞에, 흔한 태그는 흐리게 뒤에."""
    tags = [t.strip() for t in place["tags"].split("|") if t.strip()]
    is_common = [t in COMMON_TAGS or t == place["category"] for t in tags]
    special = [t for t, c in zip(tags, is_common) if not c]
    common = [t for t, c in zip(tags, is_common) if c]
    chips = "".join(f'<span class="gb-tag">#{esc(t)}</span>' for t in special)
    chips += "".join(f'<span class="gb-tag common">#{esc(t)}</span>' for t in common)
    return f'<div class="gb-tags">{chips}</div>'


def time_html(place: dict) -> str:
    minutes = place["duration_min"].strip()
    if not minutes:
        return ""
    return (f'<span class="gb-time" title="그곳에서 보내는 예상 시간 (추정값)">'
            f'⏱ 머무는 시간 약 {esc(minutes)}분</span>')


def chips_html(conditions: dict) -> str:
    picked = ", ".join(conditions["categories"]) if conditions["categories"] else "전체 분류"
    chips = [conditions["region"], date_range_text(conditions), picked]
    return '<div class="gb-chips">' + "".join(f'<span class="gb-chip">{esc(c)}</span>' for c in chips) + "</div>"


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
def share_dialog(trip_id: str):
    trip = user_store.get_trip(trip_id)
    st.caption(f"'{trip['title']}'의 추천 결과와 서로의 찜한 리스트를 함께 볼 수 있어요.")
    to_user = st.text_input("공유할 사용자 ID")
    if st.button("공유", type="primary", use_container_width=True):
        error = user_store.share_trip(trip_id, st.session_state["user"], to_user)
        if error:
            st.error(error)
        else:
            flash(f"{to_user.strip()}님에게 공유했어요!")
            st.rerun()


@st.dialog("여행 파일 삭제", width="small")
def delete_dialog(trip_id: str):
    user_id = st.session_state["user"]
    trip = user_store.get_trip(trip_id)
    if trip is None:
        st.rerun()
    if trip["owner"] == user_id:
        st.markdown(f"**'{esc(trip['title'])}'** 파일을 삭제할까요?")
        st.caption("사진 · 소감 · 찜한 리스트가 모두 지워지고, 공유한 친구의 사물함에서도 사라져요. 되돌릴 수 없어요.")
    else:
        st.markdown(f"**'{esc(user_store.auto_title(trip['conditions']))}'** 를 내 사물함에서 뺄까요?")
        st.caption(f"{trip['owner']}님의 원래 파일은 그대로 남아요. 다시 보려면 {trip['owner']}님이 다시 공유해야 해요.")

    cancel_col, ok_col = st.columns(2)
    if cancel_col.button("취소", use_container_width=True):
        st.rerun()
    if ok_col.button("삭제", type="primary", use_container_width=True):
        error = user_store.delete_trip(trip_id, user_id)
        if error:
            st.error(error)
            return
        plan = st.session_state.get("plan")
        if plan and plan["trip_id"] == trip_id:
            st.session_state.pop("plan")  # 지금 보고 있던 계획의 파일이면 계획도 같이 닫기
        close_trip()
        flash("삭제했어요.")
        st.rerun()


# =====================================================================
# ① 첫 화면 (로그인 전)
# =====================================================================
PREVIEW_RECOMMEND = f"""
<div class="gb-preview" aria-hidden="true">
  <div class="gb-pv-row">목적지 <div class="gb-pv-field"></div></div>
  <div class="gb-pv-row">날짜 <div class="gb-pv-field"></div> ~ <div class="gb-pv-field"></div></div>
  <div class="gb-pv-cards">
    <div class="gb-pv-card"><img src="{ui_style.category_image_uri('카페')}" alt=""><div>카페 ♡</div></div>
    <div class="gb-pv-card"><img src="{ui_style.category_image_uri('문화체험')}" alt=""><div>문화체험 ♡</div></div>
  </div>
</div>"""

PREVIEW_LINK = f"""
<div class="gb-preview" aria-hidden="true">
  <div class="gb-pv-link">
    <div class="gb-pv-card"><img src="{ui_style.category_image_uri('전시')}" alt=""><div>전시 ♡</div></div>
    <div class="gb-pv-arrow">👆 클릭<b>→</b></div>
    <div class="gb-pv-browser">
      <div class="gb-pv-bar"><span></span><span></span><span></span><div class="gb-pv-url">원래 안내 페이지</div></div>
      <div class="gb-pv-page"><i></i><i></i><i></i><i></i></div>
    </div>
  </div>
  <div style="text-align:center"><span class="gb-pv-hint">그림을 누르면 원래 페이지로!</span></div>
</div>"""

PREVIEW_SHARE = """
<div class="gb-preview" aria-hidden="true">
  <div style="font-family:'Jua',sans-serif;font-size:1.2rem">본 파일 공유..</div>
  <div class="gb-pv-row">공유할 사용자 ID <div class="gb-pv-field"></div></div>
  <div style="text-align:center"><span class="gb-pv-btn">공유</span></div>
  <div class="gb-pv-row" style="margin-top:16px">❤️ 내 찜 3곳 · ❤️ 친구의 찜 2곳</div>
</div>"""

PREVIEW_LOCKER = f"""
<div class="gb-preview" aria-hidden="true">
  <div style="font-family:'Jua',sans-serif;font-size:1.2rem;margin-bottom:10px">예전 여행 기획 사물함</div>
  <div class="gb-pv-files">
    <div class="gb-pv-file"><img src="{ui_style.category_image_uri('여행')}" alt=""><div>성수 11.11~11.13</div></div>
    <div class="gb-pv-file"><img src="{ui_style.category_image_uri('맛집')}" alt=""><div>홍대 맛집 투어</div></div>
    <div class="gb-pv-file"><img src="{ui_style.category_image_uri('전시')}" alt=""><div>혼자 떠난 날</div></div>
  </div>
</div>"""


def render_feature(title: str, text: str, preview: str, preview_left: bool):
    cols = st.columns(2, gap="large", vertical_alignment="center")
    text_html = f'<div class="gb-feature-title">{title}</div><div class="gb-feature-text">{text}</div>'
    (cols[0] if preview_left else cols[1]).markdown(preview, unsafe_allow_html=True)
    (cols[1] if preview_left else cols[0]).markdown(text_html, unsafe_allow_html=True)
    st.write("")


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

    render_feature(
        "기능 1 · 맞춤 장소 추천",
        "목적지, 날짜, 꼭 체험해 보고 싶은 것을 고르면 성수·홍대의 음식점, 카페, 문화체험 등을 추천해 드려요. "
        "마음에 드는 곳은 하트로 찜해 두세요.",
        PREVIEW_RECOMMEND, preview_left=True,
    )
    render_feature(
        "기능 2 · 동행과 공유",
        "함께 여행하는 친구의 아이디를 입력하면 이번 여행의 추천 결과를 공유해요. "
        "공유한 여행에서는 서로의 찜한 리스트를 함께 볼 수 있어요.",
        PREVIEW_SHARE, preview_left=False,
    )
    render_feature(
        "기능 3 · 그림을 누르면 원래 페이지로",
        "추천 카드의 그림을 누르면 그 장소의 원래 안내 페이지가 새 탭으로 열려요. "
        "영업시간, 위치, 가격 같은 자세한 정보를 바로 확인할 수 있어요.",
        PREVIEW_LINK, preview_left=True,
    )
    render_feature(
        "기능 4 · 예전 여행 기획 사물함",
        "계획을 다 세우고 [사물함에 저장]을 누르면 찜한 곳과 함께 사물함에 보관돼요. "
        "여행 이름을 바꾸고, 사진과 소감을 남겨 두었다가 언제든 다시 꺼내 볼 수 있어요.",
        PREVIEW_LOCKER, preview_left=False,
    )

    st.markdown('<div class="gb-footer">TEAM GIMBAP · 2026 연합 해커톤</div>', unsafe_allow_html=True)


# =====================================================================
# 메인 화면 공통: 머리 부분
# =====================================================================
def avatar_font_size(user_id: str) -> str:
    n = len(user_id)
    if n <= 4:
        return "1.5rem"
    if n <= 7:
        return "1.15rem"
    if n <= 11:
        return "0.9rem"
    return "0.72rem"


def render_header(user_id: str):
    cols = st.columns([1.1, 5.2, 2.0, 1.2], vertical_alignment="center")
    cols[0].markdown(ui_style.logo_html("small"), unsafe_allow_html=True)
    cols[1].markdown(
        '<div class="gb-tagline">사용자의 예산, 여행 취향, 일정에 맞는<br>'
        '여가활동 · 맛집 · 랜드마크 · 문화체험 · 교류 서비스입니다.</div>',
        unsafe_allow_html=True,
    )
    with cols[2]:
        st.markdown(f'<div class="gb-userid" title="{esc(user_id)}"><b>ID:</b>{esc(user_id)}</div>',
                    unsafe_allow_html=True)
        if st.button("로그아웃", key="logout"):
            st.session_state.clear()
            flash("로그아웃했어요.")
            st.rerun()
    cols[3].markdown(
        f'<div class="gb-avatar" style="font-size:{avatar_font_size(user_id)}" '
        f'role="img" aria-label="프로필: {esc(user_id)}">{esc(user_id)}</div>',
        unsafe_allow_html=True,
    )


# =====================================================================
# ④ 이번 여행 기획 폼
# =====================================================================
def render_trip_form(user_id: str, regions: list[str], categories: list[str]):
    st.write("")
    _, center, _ = st.columns([1, 6, 1])
    with center, st.form("trip_form"):
        st.markdown('<div class="gb-form-title">이번 여행 기획</div>', unsafe_allow_html=True)
        region = st.selectbox("목적지", regions)

        today = dt.date.today()
        date_cols = st.columns([5, 0.5, 5], vertical_alignment="bottom")
        start = date_cols[0].date_input("날짜 (시작)", value=today, min_value=today)
        date_cols[1].markdown("<div style='text-align:center;padding-bottom:0.45rem;font-size:1.3rem'>~</div>",
                              unsafe_allow_html=True)
        end = date_cols[2].date_input("날짜 (끝)", value=today + dt.timedelta(days=2), min_value=today)

        picked = st.multiselect("꼭 체험해 보고 싶은 것", categories, placeholder="선택하지 않으면 전체에서 추천해요")
        submitted = st.form_submit_button("확인", type="primary", use_container_width=True)

    if submitted:
        if end < start:
            st.warning("끝나는 날짜가 시작 날짜보다 빠를 수 없어요.")
            return
        conditions = {
            "region": region,
            "start_date": start.isoformat(),  # 예: "2026-11-14"
            "end_date": end.isoformat(),
            "categories": picked,             # 비어 있으면 전체
        }
        start_plan(user_id, conditions)
        st.session_state["shown_main"] = PAGE_SIZE


# =====================================================================
# 이번 여행 계획 (session_state["plan"])
#   [확인]  → 추천만 보여 줌. 아직 사물함에 없음 (trip_id = None). 하트는 여기 임시로 기억.
#   [사물함에 저장] 또는 공유 버튼 → 사물함에 저장 (trip_id 생김). 그다음 하트는 바로 파일에 저장.
# =====================================================================
def plan_hearts(plan: dict, user_id: str) -> list[str]:
    if plan["trip_id"]:
        trip = user_store.get_trip(plan["trip_id"])
        return list(trip["favorites"].get(user_id, [])) if trip else []
    return list(plan["favorites"])


def start_plan(user_id: str, conditions: dict):
    hearts = []
    old = st.session_state.get("plan")
    if old and old["conditions"]["region"] == conditions["region"]:
        hearts = plan_hearts(old, user_id)  # 같은 목적지에서 조건만 바꾸면 눌러 둔 하트는 그대로
    saved = user_store.find_my_trip(user_id, conditions)
    if saved:
        hearts += [p for p in saved["favorites"].get(user_id, []) if p not in hearts]

    already_saved = (saved is not None and saved["conditions"] == conditions
                     and set(hearts) <= set(saved["favorites"].get(user_id, [])))
    st.session_state["plan"] = {
        "conditions": conditions,
        "favorites": hearts,
        "trip_id": saved["trip_id"] if already_saved else None,
    }


def toggle_plan_heart(place_id: str):
    hearts = st.session_state["plan"]["favorites"]
    if place_id in hearts:
        hearts.remove(place_id)
    else:
        hearts.append(place_id)


def save_plan(user_id: str) -> str:
    plan = st.session_state["plan"]
    plan["trip_id"] = user_store.save_trip(user_id, plan["conditions"], plan["favorites"])
    return plan["trip_id"]


def on_save_click(user_id: str):
    save_plan(user_id)
    flash("이번 여행을 사물함에 저장했어요.")


# =====================================================================
# 추천 카드 (메인 화면과 여행 자세히 보기에서 같이 씀)
# =====================================================================
def render_place_card(place: dict, liked: bool, key_prefix: str, on_heart, heart_args: tuple):
    """on_heart(*heart_args, place_id): 하트를 눌렀을 때 부를 함수 (저장 전/후에 따라 다름)."""
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
        heart_col.button(
            "❤️" if liked else "♡",
            key=f"{key_prefix}_heart_{place['place_id']}",
            help="찜 취소" if liked else "찜하기",
            on_click=on_heart,
            args=(*heart_args, place["place_id"]),
        )
        st.markdown(
            f'{tags_html(place)}<div class="gb-card-bottom">{cost_html(place)}{time_html(place)}</div>',
            unsafe_allow_html=True,
        )


def show_more(shown_key: str):
    st.session_state[shown_key] = st.session_state.get(shown_key, PAGE_SIZE) + PAGE_SIZE


def render_recommendations(conditions: dict, liked: set, key_prefix: str, on_heart, heart_args: tuple):
    places = get_recommendations(conditions)
    if not places:
        st.info("조건에 맞는 장소가 없어요. 꼭 체험해 보고 싶은 것을 바꿔 보세요.")
        return
    shown_key = f"shown_{key_prefix}"
    shown = places[: st.session_state.get(shown_key, PAGE_SIZE)]

    cols = st.columns(2, gap="medium")
    for i, place in enumerate(shown):
        with cols[i % 2]:
            render_place_card(place, place["place_id"] in liked, key_prefix, on_heart, heart_args)

    if len(shown) < len(places):
        st.button(f"더 보기 ({len(shown)}/{len(places)})", key=f"more_{key_prefix}",
                  on_click=show_more, args=(shown_key,), use_container_width=True)


def render_share_button(trip_id: str, key: str):
    if st.button(":material/group:", key=key, help="동행에게 공유하기"):
        share_dialog(trip_id)


def render_delete_button(trip_id: str, help_text: str):
    if st.button(":material/delete:", key="delete_trip", help=help_text):
        delete_dialog(trip_id)


# =====================================================================
# ⑤ 이번 여행 추천 결과
# =====================================================================
def render_results(user_id: str):
    plan = st.session_state.get("plan")
    if plan is None:
        return
    if plan["trip_id"] and user_store.get_trip(plan["trip_id"]) is None:
        plan["trip_id"] = None  # 저장했던 파일이 없어졌으면 다시 '저장 전'으로

    st.write("")
    head = st.columns([6, 2.2, 0.8], vertical_alignment="center")
    head[0].markdown('<div class="gb-section-title">추천 내용</div>', unsafe_allow_html=True)
    head[1].markdown('<div class="gb-share-label">Share the file with</div>', unsafe_allow_html=True)
    with head[2]:
        if st.button(":material/group:", key="share_main",
                     help="동행에게 공유하기 (저장 전이면 사물함에 함께 저장돼요)"):
            if not plan["trip_id"]:
                save_plan(user_id)  # 공유하려면 파일이 있어야 하므로 자동으로 저장
                st.toast("공유하려고 이번 여행을 사물함에 먼저 저장했어요.")
            share_dialog(plan["trip_id"])

    st.markdown(chips_html(plan["conditions"]), unsafe_allow_html=True)
    if plan["trip_id"]:
        on_heart, heart_args = user_store.toggle_favorite, (plan["trip_id"], user_id)
    else:
        on_heart, heart_args = toggle_plan_heart, ()
    render_recommendations(plan["conditions"], set(plan_hearts(plan, user_id)), "main", on_heart, heart_args)

    # 계획이 끝나면 맨 아래에서 저장
    st.write("")
    if plan["trip_id"]:
        st.button("✓ 사물함에 저장됨", key="saved_main", disabled=True, use_container_width=True)
        st.markdown('<div class="gb-save-note">이제부터 누르는 하트는 바로 저장돼요. '
                    '아래 사물함에서 사진과 소감도 남겨 보세요.</div>', unsafe_allow_html=True)
    else:
        st.button("사물함에 저장", key="save_main", type="primary", use_container_width=True,
                  on_click=on_save_click, args=(user_id,))
        st.markdown('<div class="gb-save-note">아직 저장하지 않았어요. 계획을 다 세웠으면 '
                    '[사물함에 저장]을 눌러 주세요. 찜한 곳도 함께 저장돼요.</div>', unsafe_allow_html=True)


# =====================================================================
# 예전 여행 기획 사물함
# =====================================================================
def trip_image_uri(trip: dict, user_id: str) -> str:
    """주인이 올린 사진이 있으면 사진, 없으면 기본 그림. 공유받은 사람에게는 사진을 보여주지 않는다."""
    path = user_store.photo_path(trip)
    if path and trip["owner"] == user_id:
        return ui_style.photo_uri(path)
    return ui_style.category_image_uri("여행")


def open_trip(trip_id: str):
    st.session_state["open_trip_id"] = trip_id
    st.session_state["shown_detail"] = PAGE_SIZE


def close_trip():
    st.session_state.pop("open_trip_id", None)


def render_file_card(trip: dict, user_id: str):
    is_owner = trip["owner"] == user_id
    title = trip["title"] if is_owner else user_store.auto_title(trip["conditions"])
    if is_owner:
        first_line = trip["notes"].splitlines()[0] if trip["notes"] else ""
        note = esc(first_line) if first_line else '<span style="opacity:.55">소감을 남겨 보세요</span>'
    else:
        note = f'<span class="gb-file-shared">{esc(trip["owner"])}님이 공유</span>'

    st.markdown(
        f'<div class="gb-file-img"><img src="{trip_image_uri(trip, user_id)}" alt="{esc(title)} 사진"></div>'
        f'<div class="gb-file-meta"><span class="gb-file-name">{esc(title)}</span>'
        f'<span class="gb-file-date">{esc(date_range_text(trip["conditions"]))}</span></div>'
        f'<div class="gb-file-note">{note}</div>',
        unsafe_allow_html=True,
    )
    st.button("열어 보기", key=f"open_{trip['trip_id']}", on_click=open_trip, args=(trip["trip_id"],),
              use_container_width=True)
    st.write("")


def render_locker(user_id: str):
    st.markdown('<div class="gb-double-line"></div>', unsafe_allow_html=True)
    st.markdown('<div class="gb-locker-title">예전 여행 기획 사물함</div>'
                '<div class="gb-locker-sub">[사물함에 저장]을 누른 여행과 공유받은 여행이 여기에 모여요.</div>',
                unsafe_allow_html=True)
    trips = user_store.list_trips_for(user_id)
    if not trips:
        st.info("아직 저장된 여행이 없어요. 위에서 이번 여행을 기획한 뒤 맨 아래 [사물함에 저장]을 눌러 보세요.")
        return
    cols = st.columns(3, gap="large")
    for i, trip in enumerate(trips):
        with cols[i % 3]:
            render_file_card(trip, user_id)


# =====================================================================
# 사물함 → 여행 자세히 보기
# 순서: 사진 → 여행 이름 → 나의 소감 → 공유 → 찜한 리스트 → 추천 결과
# =====================================================================
def render_owner_info(trip: dict, user_id: str):
    st.markdown(f'<div class="gb-detail-photo"><img src="{trip_image_uri(trip, user_id)}" alt="여행 사진"></div>',
                unsafe_allow_html=True)
    st.write("")
    with st.form(f"edit_{trip['trip_id']}"):
        title = st.text_input("여행 이름", value=trip["title"], max_chars=40)
        notes = st.text_area("나의 소감", value=trip["notes"], max_chars=1000,
                             placeholder="예) 해피 모먼트: 비가 와서 들어간 카페가 최고였다!")
        photo = st.file_uploader("사진 바꾸기 (png · jpg · webp, 5MB 이하)", type=["png", "jpg", "jpeg", "webp"])
        saved = st.form_submit_button("저장", type="primary")
    if saved:
        error = user_store.update_trip_info(trip["trip_id"], user_id, title, notes)
        if not error and photo is not None:
            error = user_store.set_trip_photo(trip["trip_id"], user_id, photo.name, photo.getvalue())
        if error:
            st.error(error)
        else:
            flash("저장했어요.")
            st.rerun()

    # 왼쪽: 공유 상태 글자 + 바로 옆에 공유(사람) 아이콘 / 오른쪽 끝: 휴지통
    left, right = st.columns([6, 1], vertical_alignment="center")
    with left, st.container(horizontal=True, vertical_alignment="center", gap="small"):
        if trip["shared_with"]:
            names = ", ".join(trip["shared_with"])
            st.markdown(f'<div class="gb-share-line">🤝 {esc(names)}님과 공유한 여행이에요</div>',
                        unsafe_allow_html=True, width="content")
        else:
            st.markdown('<div class="gb-share-line">아직 아무와도 공유하지 않았어요</div>',
                        unsafe_allow_html=True, width="content")
        render_share_button(trip["trip_id"], key="share_detail")
    with right:
        render_delete_button(trip["trip_id"], help_text="이 여행 파일 삭제")


def render_favorites(trip: dict, user_id: str, places_by_id: dict):
    st.markdown('<div class="gb-subtitle">찜한 리스트</div>', unsafe_allow_html=True)
    people = [trip["owner"]] + trip["shared_with"]
    people.sort(key=lambda p: p != user_id)  # 내 찜을 맨 앞에
    cols = st.columns(min(len(people), 3))
    for i, person in enumerate(people):
        label = "내 찜" if person == user_id else f"{person}님의 찜"
        items = []
        for place_id in trip["favorites"].get(person, []):
            place = places_by_id.get(place_id)
            if place:
                items.append(f'<li><a href="{esc(place["source_url"])}" target="_blank" rel="noopener noreferrer">'
                             f'{esc(place["name"])}</a> · {esc(place["category"])}</li>')
        body = f"<ul>{''.join(items)}</ul>" if items else '<div style="opacity:.6">아직 찜한 곳이 없어요</div>'
        cols[i % len(cols)].markdown(f'<div class="gb-fav-box"><b>❤️ {esc(label)} ({len(items)})</b>{body}</div>',
                                     unsafe_allow_html=True)


def render_trip_detail(user_id: str, trip_id: str, places_by_id: dict):
    trip = user_store.get_trip(trip_id)
    if trip is None or not user_store.can_view(trip, user_id):
        close_trip()
        st.warning("이 여행을 찾을 수 없어요.")
        return

    # 주의: 카드 안에 이미 칸(columns)이 있어서, 여기서 한 번 더 칸으로 감싸면 Streamlit 중첩 제한에 걸림
    st.button("← 사물함으로 돌아가기", key="back_to_locker", on_click=close_trip)
    if trip["owner"] == user_id:
        render_owner_info(trip, user_id)
    else:
        st.markdown(f'<div class="gb-detail-title">{esc(user_store.auto_title(trip["conditions"]))}</div>',
                    unsafe_allow_html=True)
        left, right = st.columns([6, 1], vertical_alignment="center")
        left.markdown(f'<div class="gb-share-line">🤝 {esc(trip["owner"])}님이 공유한 여행이에요</div>',
                      unsafe_allow_html=True)
        with right:
            render_delete_button(trip["trip_id"], help_text="내 사물함에서 빼기")

    render_favorites(trip, user_id, places_by_id)
    st.markdown('<div class="gb-subtitle">추천 결과</div>', unsafe_allow_html=True)
    st.markdown(chips_html(trip["conditions"]), unsafe_allow_html=True)
    render_recommendations(trip["conditions"], set(trip["favorites"].get(user_id, [])), "detail",
                           user_store.toggle_favorite, (trip["trip_id"], user_id))


# =====================================================================
# 메인 화면 (로그인 후)
# =====================================================================
def render_main(user_id: str):
    all_places = load_csv("places.csv")
    places_by_id = {p["place_id"]: p for p in all_places}

    render_header(user_id)
    open_id = st.session_state.get("open_trip_id")
    if open_id:
        render_trip_detail(user_id, open_id, places_by_id)
        return

    regions = sorted({p["region"] for p in all_places})
    categories = sorted({p["category"] for p in all_places})
    render_trip_form(user_id, regions, categories)
    render_results(user_id)
    render_locker(user_id)


# =====================================================================
# 시작점: 로그인 여부에 따라 ① 또는 메인 화면
# =====================================================================
if "flash" in st.session_state:
    st.toast(st.session_state.pop("flash"))

if "user" in st.session_state:
    render_main(st.session_state["user"])
else:
    render_landing()
