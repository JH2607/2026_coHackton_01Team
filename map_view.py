"""지도 담당 파일 (프론트엔드) — 왼쪽 지도 + 오른쪽 '찜한 리스트'.

- 처음에는 고른 지역 근처의 지도만 보여 준다.
- 하트(찜)를 누를 때마다 그 장소가 지도에 핀으로 추가되고, 핀 번호 = 찜한 순서 (카드 오른쪽 위 번호와 같음).
- 장소에 좌표(lat, lng)가 없으면 지도에는 못 찍고, 오른쪽 목록에 "좌표 없음"으로 표시한다.

장소 한 개의 모양 (팀 데이터 형식 초안 3번 '검증 후 목록'과 같은 이름)
  {"name", "category", "reason", "address", "lat", "lng", "place_url"}   # lat/lng 없으면 None

지도 두 가지
  - 기본 지도 (folium + OpenStreetMap): 키 필요 없음
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

# 지역을 고르면 처음 보여 줄 지도 중심 (영어 위키백과 좌표, 2026-11-07 확인)
#   성수: Seongsu-dong 문서의 동 중심 좌표 / 홍대: Hongik University station 문서 좌표
REGION_CENTER = {
    "성수": (37.5442, 127.0494),
    "홍대": (37.55667, 126.92361),
}
SEOUL_CENTER = (37.5663, 126.9779)  # 목록에 없는 지역일 때: 서울시청 부근 (대략)


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
    link = (f'<br><a href="{_esc(place["place_url"])}" target="_blank">원래 페이지 열기</a>'
            if place.get("place_url") else "")
    return f'<b>{number}. {_esc(place["name"])}</b> <small>({_esc(place["category"])})</small>{link}'


def _has_coords(place: dict) -> bool:
    return place.get("lat") is not None and place.get("lng") is not None


# ---------------------------------------------------------------------
# 기본 지도 (folium)
# ---------------------------------------------------------------------
def folium_map_html(numbered: list[tuple[int, dict]], center: tuple[float, float]) -> str:
    """numbered: [(찜한 순서 번호, 장소), ...] 중 좌표가 있는 것만."""
    fmap = folium.Map(location=center, zoom_start=15, tiles="OpenStreetMap", control_scale=True)
    for number, place in numbered:
        folium.Marker(
            (place["lat"], place["lng"]),
            icon=folium.DivIcon(html=_pin_html(number), icon_size=(30, 30), icon_anchor=(15, 15)),
            tooltip=f"{number}. {_esc(place['name'])}",
            popup=folium.Popup(_popup_html(place, number), max_width=260),
        ).add_to(fmap)
    if len(numbered) == 1:
        fmap.location = [numbered[0][1]["lat"], numbered[0][1]["lng"]]
    elif len(numbered) > 1:
        lats = [p["lat"] for _, p in numbered]
        lngs = [p["lng"] for _, p in numbered]
        fmap.fit_bounds([[min(lats), min(lngs)], [max(lats), max(lngs)]], padding=(40, 40), max_zoom=17)
    return fmap.get_root().render()


# ---------------------------------------------------------------------
# 카카오 지도 (JavaScript SDK) — 키 · 도메인 등록이 안 되어 있으면 지도 안에 안내 문구를 띄움
# ---------------------------------------------------------------------
def kakao_map_html(numbered: list[tuple[int, dict]], center: tuple[float, float], js_key: str) -> str:
    data = [{"n": n, "name": p["name"], "lat": p["lat"], "lng": p["lng"], "url": p.get("place_url", "")}
            for n, p in numbered]
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
  const CENTER = [{center[0]}, {center[1]}];
  let drawn = false;
  function fail(msg) {{ const e = document.getElementById('err'); e.style.display = 'block'; e.textContent = msg; }}
  function draw() {{
    const map = new kakao.maps.Map(document.getElementById('map'), {{
      center: new kakao.maps.LatLng(CENTER[0], CENTER[1]), level: 4 }});
    const bounds = new kakao.maps.LatLngBounds();
    PLACES.forEach(p => {{
      const pos = new kakao.maps.LatLng(p.lat, p.lng);
      bounds.extend(pos);
      const pin = document.createElement('div');
      pin.className = 'pin'; pin.textContent = p.n; pin.title = p.n + '. ' + p.name;
      if (p.url) pin.onclick = () => window.open(p.url, '_blank');
      new kakao.maps.CustomOverlay({{ position: pos, content: pin, yAnchor: 0.5 }}).setMap(map);
    }});
    if (PLACES.length === 1) map.setCenter(new kakao.maps.LatLng(PLACES[0].lat, PLACES[0].lng));
    if (PLACES.length > 1) map.setBounds(bounds);
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
# 오른쪽 '찜한 리스트'
# ---------------------------------------------------------------------
def picks_list_html(picks: list[dict]) -> str:
    title = '<div class="gb-picks-title">찜한 리스트</div>'
    if not picks:
        return title + '<div class="gb-picks-empty">아직 찜한 곳이 없어요. 아래 추천 장소에서 ♡를 누르면 지도에 번호가 생겨요.</div>'
    rows = []
    for number, place in enumerate(picks, start=1):
        name = _esc(place["name"])
        if place.get("place_url"):
            name = f'<a href="{_esc(place["place_url"])}" target="_blank" rel="noopener noreferrer">{name}</a>'
        address = f'<div class="gb-course-addr">{_esc(place["address"])}</div>' if place.get("address") else ""
        no_pin = "" if _has_coords(place) else '<div class="gb-course-nopin">좌표 정보가 없어서 지도에는 아직 표시하지 못했어요.</div>'
        rows.append(
            f'<div class="gb-course-row"><div class="gb-course-num">{number}</div><div>'
            f'<div class="gb-course-name">{name} <span class="gb-course-cat">{_esc(place["category"])}</span></div>'
            f'{address}{no_pin}</div></div>'
        )
    return title + '<div class="gb-course-list">' + "".join(rows) + "</div>"


def render_picks_map(picks: list[dict], region: str, key: str) -> None:
    """picks: 찜한 순서대로 정렬된 장소 목록. key: 같은 화면에 지도가 여러 개일 때 구분용."""
    center = REGION_CENTER.get(region, SEOUL_CENTER)
    numbered = [(n, p) for n, p in enumerate(picks, start=1) if _has_coords(p)]

    kind = "기본 지도"
    kakao_key = os.getenv("KAKAO_JS_KEY", "").strip()
    if kakao_key:
        kind = st.radio("지도 종류", ["카카오 지도", "기본 지도"], horizontal=True, key=f"map_kind_{key}")

    map_col, list_col = st.columns([3, 2], gap="medium")
    with map_col:
        page = kakao_map_html(numbered, center, kakao_key) if kind == "카카오 지도" else folium_map_html(numbered, center)
        components.html(page, height=MAP_HEIGHT)
    with list_col:
        st.markdown(picks_list_html(picks), unsafe_allow_html=True)
