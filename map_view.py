"""지도 담당 파일 (프론트엔드) — 추천 코스를 지도에 번호로 표시한다.

입력: '검증 후 목록' (팀 데이터 형식 초안 3번, 카카오 검증 함수가 돌려줄 모양)
  [{"name", "category", "reason", "kakao_id", "address", "lat", "lng", "place_url"}, ...]
  - 리스트 순서 = 방문 순서 → 지도에 1, 2, 3 … 번호를 붙이고 순서대로 선으로 연결
  - 선은 두 지점을 잇는 직선이에요 (실제 도보 경로가 아님)

지도 두 가지
  - 기본 지도 (folium + OpenStreetMap): 키 없이 바로 사용
  - 카카오 지도: .env에 KAKAO_JS_KEY 가 있을 때만 고를 수 있음
      카카오 개발자 앱에서 ① [카카오맵] > [사용 설정] ON ② JavaScript SDK 도메인에 http://localhost:8501 등록
      (Streamlit을 다른 포트로 실행하면 그 주소도 등록해야 함)
"""

import html
import json
import os

import folium
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv()  # .env 파일의 KAKAO_JS_KEY 읽기 (GitHub에는 올리지 않음)

MAP_HEIGHT = 440
LINE_COLOR = "#F07B2A"

# ---------------------------------------------------------------------
# 예시 데이터: AI 추천 · 카카오 검증 함수가 연결되기 전에 지도 화면을 확인하는 용도
# 좌표 출처: 영어 위키백과 각 문서에 표시된 좌표 (2026-11-07 확인)
#   서울숲, 서울숲역(Seoul-forest station), 성수동(Seongsu-dong 문서의 동 중심 좌표),
#   경의선숲길(Gyeongui Line Forest Park), 홍대입구역(Hongik University station), 상수역(Sangsu station)
# 카카오 ID · 주소 · 링크는 검증 함수가 채울 부분이라 비워 둠
# ---------------------------------------------------------------------
_SAMPLE_REASON = "예시 데이터예요. 카카오 검증 함수가 연결되면 실제 추천 결과로 바뀌어요."


def _sample(name: str, lat: float, lng: float) -> dict:
    return {"name": name, "category": "예시", "reason": _SAMPLE_REASON,
            "kakao_id": "", "address": "", "lat": lat, "lng": lng, "place_url": ""}


SAMPLE_COURSE = {
    "성수": [
        _sample("서울숲", 37.5446250, 127.0398444),
        _sample("서울숲역", 37.543647, 127.044686),
        _sample("성수동 (동네 중심)", 37.5442, 127.0494),
    ],
    "홍대": [
        _sample("경의선숲길", 37.5593, 126.9248),
        _sample("홍대입구역", 37.55667, 126.92361),
        _sample("상수역", 37.54778, 126.92250),
    ],
}


def _esc(text) -> str:
    return html.escape(str(text), quote=True)


def _pin_html(number: int) -> str:
    return (
        '<div style="width:30px;height:30px;border-radius:50%;background:#F6C945;'
        'border:2.5px solid #1F2B24;box-shadow:2px 2px 0 #1F2B24;display:flex;align-items:center;'
        'justify-content:center;font:800 14px sans-serif;color:#1F2B24;">'
        f"{number}</div>"
    )


def _popup_html(place: dict, number: int) -> str:
    link = (f'<br><a href="{_esc(place["place_url"])}" target="_blank">카카오맵에서 보기</a>'
            if place.get("place_url") else "")
    return (f'<b>{number}. {_esc(place["name"])}</b> <small>({_esc(place["category"])})</small>'
            f'<br><span style="font-size:12px">{_esc(place.get("reason", ""))}</span>{link}')


# ---------------------------------------------------------------------
# 기본 지도 (folium)
# ---------------------------------------------------------------------
def folium_map_html(places: list[dict]) -> str:
    points = [(p["lat"], p["lng"]) for p in places]
    center = (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))
    fmap = folium.Map(location=center, zoom_start=16, tiles="OpenStreetMap", control_scale=True)

    if len(points) > 1:  # 방문 순서대로 직선 연결
        folium.PolyLine(points, color=LINE_COLOR, weight=4, opacity=0.9, dash_array="8 8").add_to(fmap)
    for number, place in enumerate(places, start=1):
        folium.Marker(
            (place["lat"], place["lng"]),
            icon=folium.DivIcon(html=_pin_html(number), icon_size=(30, 30), icon_anchor=(15, 15)),
            tooltip=f"{number}. {_esc(place['name'])}",
            popup=folium.Popup(_popup_html(place, number), max_width=260),
        ).add_to(fmap)
    if len(points) > 1:
        lats, lngs = [p[0] for p in points], [p[1] for p in points]
        fmap.fit_bounds([[min(lats), min(lngs)], [max(lats), max(lngs)]], padding=(40, 40))
    return fmap.get_root().render()


# ---------------------------------------------------------------------
# 카카오 지도 (JavaScript SDK) — 키 · 도메인 등록이 안 되어 있으면 지도 안에 안내 문구를 띄움
# ---------------------------------------------------------------------
def kakao_map_html(places: list[dict], js_key: str) -> str:
    data = [{"n": i, "name": p["name"], "lat": p["lat"], "lng": p["lng"], "url": p.get("place_url", "")}
            for i, p in enumerate(places, start=1)]
    data_js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    key_js = json.dumps(js_key)
    return f"""
<div id="map" style="width:100%;height:{MAP_HEIGHT - 10}px;border-radius:14px;border:1.5px solid #1F2B24;"></div>
<div id="err" style="display:none;font:15px sans-serif;color:#7A2E12;background:#FFF1E6;border:1.5px solid #F07B2A;
     border-radius:10px;padding:12px;margin-top:-{MAP_HEIGHT - 30}px;position:relative;"></div>
<style>
  .pin {{ width:30px;height:30px;border-radius:50%;background:#F6C945;border:2.5px solid #1F2B24;
          box-shadow:2px 2px 0 #1F2B24;display:flex;align-items:center;justify-content:center;
          font:800 14px sans-serif;color:#1F2B24;cursor:pointer; }}
</style>
<script>
  const PLACES = {data_js};
  let drawn = false;
  function fail(msg) {{ const e = document.getElementById('err'); e.style.display = 'block'; e.textContent = msg; }}
  function draw() {{
    const map = new kakao.maps.Map(document.getElementById('map'), {{
      center: new kakao.maps.LatLng(PLACES[0].lat, PLACES[0].lng), level: 4 }});
    const bounds = new kakao.maps.LatLngBounds();
    const path = [];
    PLACES.forEach(p => {{
      const pos = new kakao.maps.LatLng(p.lat, p.lng);
      path.push(pos); bounds.extend(pos);
      const pin = document.createElement('div');
      pin.className = 'pin'; pin.textContent = p.n; pin.title = p.n + '. ' + p.name;
      if (p.url) pin.onclick = () => window.open(p.url, '_blank');
      new kakao.maps.CustomOverlay({{ position: pos, content: pin, yAnchor: 0.5 }}).setMap(map);
    }});
    if (path.length > 1) {{
      new kakao.maps.Polyline({{ path: path, strokeWeight: 4, strokeColor: '{LINE_COLOR}',
                                strokeOpacity: 0.9, strokeStyle: 'dash' }}).setMap(map);
      map.setBounds(bounds);
    }}
    drawn = true;
  }}
  const sdk = document.createElement('script');
  sdk.src = 'https://dapi.kakao.com/v2/maps/sdk.js?autoload=false&appkey=' + encodeURIComponent({key_js});
  sdk.onerror = () => fail('카카오 지도를 불러오지 못했어요. 키, 도메인 등록(http://localhost:8501), [카카오맵] 사용 설정 ON을 확인해 주세요.');
  sdk.onload = () => {{
    if (!window.kakao || !window.kakao.maps) return fail('카카오 지도 SDK가 비어 있어요. 키를 확인해 주세요.');
    kakao.maps.load(draw);
  }};
  document.head.appendChild(sdk);
  setTimeout(() => {{ if (!drawn && document.getElementById('err').style.display !== 'block') fail('카카오 지도가 6초 안에 그려지지 않았어요. 키 · 도메인 등록 · 사용 설정을 확인해 주세요. 안 되면 [기본 지도]를 쓰면 돼요.'); }}, 6000);
</script>
"""


# ---------------------------------------------------------------------
# 오른쪽 목록 (번호 · 이름 · 분류 · 주소 · 추천 이유)
# ---------------------------------------------------------------------
def course_list_html(places: list[dict]) -> str:
    rows = []
    for number, place in enumerate(places, start=1):
        name = _esc(place["name"])
        if place.get("place_url"):
            name = f'<a href="{_esc(place["place_url"])}" target="_blank">{name}</a>'
        address = f'<div class="gb-course-addr">{_esc(place["address"])}</div>' if place.get("address") else ""
        rows.append(
            f'<div class="gb-course-row"><div class="gb-course-num">{number}</div><div>'
            f'<div class="gb-course-name">{name} <span class="gb-course-cat">{_esc(place["category"])}</span></div>'
            f'{address}<div class="gb-course-reason">{_esc(place.get("reason", ""))}</div></div></div>'
        )
    return '<div class="gb-course-list">' + "".join(rows) + "</div>"


def render_course(places: list[dict], key: str) -> None:
    """지도(왼쪽) + 번호 목록(오른쪽). key: 같은 화면에 지도가 여러 개일 때 구분용."""
    if not places:
        st.info("지도에 표시할 장소가 없어요.")
        return

    kind = "기본 지도"
    kakao_key = os.getenv("KAKAO_JS_KEY", "").strip()
    if kakao_key:
        kind = st.radio("지도 종류", ["카카오 지도", "기본 지도"], horizontal=True, key=f"map_kind_{key}")

    map_col, list_col = st.columns([3, 2], gap="medium")
    with map_col:
        page = kakao_map_html(places, kakao_key) if kind == "카카오 지도" else folium_map_html(places)
        components.html(page, height=MAP_HEIGHT)
    with list_col:
        st.markdown(course_list_html(places), unsafe_allow_html=True)
    st.markdown('<div class="gb-course-note">선은 방문 순서대로 두 장소를 이은 직선이에요. 실제 걷는 길과는 달라요.</div>',
                unsafe_allow_html=True)
