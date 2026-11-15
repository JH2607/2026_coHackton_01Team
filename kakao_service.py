"""카카오맵 REST API 연동 (통합 모듈): 장소 검증·좌표 검색과 도보 경로 확인.

예전에는 kakao_verifier.py(AI 추천 검증)와 kakao_service.py(지도 좌표)가 따로 있었는데,
검색·대조 규칙이 서로 달라서 이 파일 하나로 합쳤다. kakao_verifier.py는 호환용으로만 남아 있다.

  match_place(name, region, address)   장소 1곳을 카카오에서 찾아 대조 결과를 돌려줌 (핵심 함수)
  verify_places(ai_places, region)     AI 추천 목록 검증 (예전 kakao_verifier와 같은 입출력)
  resolve_place(place)                 CSV 한 행 → 지도에 쓸 장소 정보 (ui.py에서 사용)
  walking_route(ordered)               2~7곳 도보 경로

DB 좌표 일괄 채우기는 fill_kakao_coords.py 를 실행한다.

REST 키는 서버 환경변수 KAKAO_REST_API_KEY로만 읽으며 코드/HTML에 포함하지 않는다.
카카오 장소 검색 일치는 '등록 정보 확인'이며 영업 상태나 실제 운영의 보증이 아니다.
"""
from __future__ import annotations

from difflib import SequenceMatcher
from functools import lru_cache
import os
import re
import time

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = 'https://dapi.kakao.com'

# 지역 → (경도 x, 위도 y), 검색 반경(m), 구 이름. 검색 결과를 이 범위 안으로 좁힌다.
REGION_INFO = {
    '성수': {'x': 127.0557, 'y': 37.5446, 'radius': 4000, 'district': '성동구'},
    '홍대': {'x': 126.9237, 'y': 37.5563, 'radius': 4000, 'district': '마포구'},
}

# ---- 대조 결과 상태 (places.csv의 kakao_match_status 열에 그대로 들어감) ----
STATUS_OK = '일치'                 # 이름·주소(또는 구) 모두 맞음
STATUS_NAME_DIFF = '이름 다름'      # 같은 주소에 있지만 카카오 장소명이 다름 → 좌표는 채움, 사람 확인 필요
STATUS_ADDR_DIFF = '주소 다름'      # 이름은 맞지만 CSV 주소와 다른 곳 → 좌표는 채움, 이전·지점 여부 확인 필요
STATUS_ADDR_ONLY = '주소로만 좌표'  # 장소 검색 실패, CSV 주소로 좌표만 찾음 → 카카오맵 링크 없음
STATUS_NOT_FOUND = '검색 안 됨'
STATUS_ERROR = '조회 오류'
STATUS_NO_KEY = '키 없음'

# 좌표를 지도에 써도 되는 상태
COORD_STATUSES = (STATUS_OK, STATUS_NAME_DIFF, STATUS_ADDR_DIFF, STATUS_ADDR_ONLY)
# 사람이 확인해야 하는 상태 (안 되는 곳 목록에 들어감)
REVIEW_STATUSES = (STATUS_NAME_DIFF, STATUS_ADDR_DIFF, STATUS_ADDR_ONLY, STATUS_NOT_FOUND, STATUS_ERROR)

NAME_THRESHOLD = 0.8
ADDRESS_ONLY = '@주소'  # kakao_overrides.csv의 query에 쓰면 주소로만 좌표
_REGION_WORDS = ('성수동', '성수', '홍대입구', '홍대', '연남동', '연남', '서울숲')
_VAGUE_ADDRESS = re.compile(r'일대|생활권|부근|인근')


def rest_key() -> str:
    return os.getenv('KAKAO_REST_API_KEY', '').strip()


def _get(path: str, params: dict) -> dict:
    key = rest_key()
    if not key:
        raise RuntimeError('KAKAO_REST_API_KEY가 설정되지 않았어요.')
    response = requests.get(
        BASE + path,
        params=params,
        headers={'Authorization': f'KakaoAK {key}'},
        timeout=(3, 8),
    )
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# 문자열 정리 도구
# ---------------------------------------------------------------------------
def _norm(value: str) -> str:
    return re.sub(r'[^\w가-힣]', '', str(value).casefold()).replace('_', '')


def _district(address: str) -> str:
    hit = re.search(r'(\S+구)(?=\s|$)', str(address))
    return hit.group(1) if hit else ''


def _valid_coords(lat, lng) -> bool:
    try:
        return 33 <= float(lat) <= 39 and 124 <= float(lng) <= 132
    except (TypeError, ValueError):
        return False


def is_vague_address(address: str) -> bool:
    """'홍대 일대', '홍대 생활권'처럼 번지가 없어 주소로 대조할 수 없는 경우."""
    address = str(address or '')
    return bool(_VAGUE_ADDRESS.search(address)) or not _address_keys(address)


def _road_keys(address: str) -> list[str]:
    """'서울 성동구 뚝섬로 273' → ['뚝섬로273']"""
    return list(dict.fromkeys(road + num for road, num in
                              re.findall(r'(\S+(?:로|길))\s*(\d+(?:-\d+)?)', str(address or ''))))


def _jibun_keys(address: str) -> list[str]:
    """'서울 성동구 성수동2가 289-211' → ['성수동2가289-211']"""
    return list(dict.fromkeys(dong + num for dong, num in
                              re.findall(r'(\S+(?:동|가))\s+(\d+(?:-\d+)?)', str(address or ''))))


def _address_keys(address: str) -> list[str]:
    return _road_keys(address) + _jibun_keys(address)


def _address_base(address: str) -> str:
    """주소 검색용: 번지까지만 남김. '성수이로7길 27 106-2호' → '... 성수이로7길 27'."""
    text = str(address or '')
    hit = (re.match(r'^.*?\S+(?:로|길)\s*\d+(?:-\d+)?', text)
           or re.match(r'^.*?\S+(?:동|가)\s+\d+(?:-\d+)?', text))
    return hit.group(0).strip() if hit else text.strip()


def name_aliases(name: str) -> list[str]:
    """검색에 쓸 이름 후보. 예) '디뮤지엄 (D MUSEUM)' → ['디뮤지엄 (D MUSEUM)', '디뮤지엄', 'D MUSEUM']
    '와이덴 성수' → ['와이덴 성수', '와이덴']"""
    name = str(name or '').strip()
    base = re.sub(r'\s*[\(（].*?[\)）]\s*', ' ', name).strip()
    inner = [s.strip() for s in re.findall(r'[\(（](.*?)[\)）]', name) if s.strip()]
    core = base
    for word in _REGION_WORDS:
        core = re.sub(rf'(^|\s){word}(점)?(?=\s|$)', ' ', core)
    core = re.sub(r'\s+', ' ', core).strip()
    out = [name, base]
    if len(_norm(core)) >= 2:
        out.append(core)
    # '카페 어니언 성수'처럼 앞에 붙은 업종명 제거
    for alias in list(out):
        stripped = re.sub(r'^(카페|cafe)\s+', '', alias, flags=re.I)
        if stripped != alias and len(_norm(stripped)) >= 2:
            out.append(stripped)
    out += [s for s in inner if len(_norm(s)) >= 2]
    return [a for a in dict.fromkeys(out) if a]


def _contains_match(target: str, candidate: str) -> bool:
    """포함 관계를 같은 장소로 볼지.
    O  '서울숲' → '서울숲공원', '대림창고 갤러리 카페' → '대림창고' (앞부분이 같음)
    X  '글로우' → '이브닝글로우'·'글로우이브닝클럽' (일부만 겹침), '경의선책거리' → 'GS25 경의선책거리점' (그 장소 안의 지점)
    """
    # 앞부분이 같아도 CSV 이름이 카카오 이름의 절반 이상이어야 인정 ('글로우' → '글로우이브닝클럽' X)
    if len(target) >= 2 and candidate.startswith(target) and len(target) * 2 >= len(candidate):
        return True
    if len(candidate) >= 3 and target.startswith(candidate):
        return True
    if len(target) >= 4 and target in candidate:
        # 'GS25 경의선책거리점'처럼 다른 상호가 앞에 붙고 '점'으로 끝나면 그 장소 안의 가게
        return not (candidate.endswith('점') and not target.endswith('점'))
    return False


def name_score(csv_name: str, kakao_name: str) -> float:
    """0~1. 같은 이름이면 1, 포함 관계면 0.9, 나머지는 문자열 유사도.

    포함 관계 기준은 _contains_match 참고."""
    candidate = _norm(kakao_name)
    best = 0.0
    for alias in name_aliases(csv_name):
        target = _norm(alias)
        if not target or not candidate:
            continue
        if target == candidate:
            return 1.0
        if _contains_match(target, candidate):
            best = max(best, 0.9)
        best = max(best, SequenceMatcher(None, target, candidate).ratio())
    return round(best, 3)


def address_match(csv_address: str, doc: dict) -> bool | None:
    """CSV 주소와 카카오 결과 주소가 같은 번지인지.

    도로명은 도로명끼리, 지번은 지번끼리만 비교한다. (서울숲처럼 카카오에 지번만 있는 곳을
    '주소 다름'으로 오판하지 않도록) 비교할 짝이 없거나 CSV 주소가 모호하면 None.
    """
    if is_vague_address(csv_address):
        return None
    pairs = [(_road_keys(csv_address), doc.get('road_address_name') or ''),
             (_jibun_keys(csv_address), doc.get('address_name') or '')]
    compared = False
    for keys, kakao in pairs:
        kakao = re.sub(r'\s+', '', kakao)
        if not keys or not kakao:
            continue
        compared = True
        # '뚝섬로273'이 '뚝섬로2730'에 잘못 걸리지 않도록 뒤에 숫자·하이픈이 오면 불일치
        if any(re.search(re.escape(key) + r'(?![\d-])', kakao) for key in keys):
            return True
    return False if compared else None


def _doc_address(doc: dict) -> str:
    return doc.get('road_address_name') or doc.get('address_name', '')


def _empty(status: str, note: str = '', candidates: list[str] | None = None) -> dict:
    return {'status': status, 'lat': None, 'lng': None, 'place_url': '',
            'kakao_name': '', 'kakao_address': '', 'kakao_id': '',
            'name_score': 0.0, 'address_match': None, 'query': '',
            'note': note, 'candidates': candidates or []}


# ---------------------------------------------------------------------------
# 핵심: 장소 1곳 대조
# ---------------------------------------------------------------------------
def _keyword_search(query: str, region: str) -> list[dict]:
    params = {'query': query, 'size': 15}
    info = REGION_INFO.get(region)
    if info:
        params.update({'x': info['x'], 'y': info['y'], 'radius': info['radius']})
    return _get('/v2/local/search/keyword.json', params).get('documents', [])


def _address_search(address: str) -> dict | None:
    # '2층', '106-2호' 같은 상세 위치는 주소 검색을 방해하므로 번지까지만 사용
    docs = _get('/v2/local/search/address.json', {'query': _address_base(address), 'size': 1}).get('documents', [])
    return docs[0] if docs else None


def match_place(name: str, region: str = '', address: str = '', *,
                queries: list[str] | None = None, pause: float = 0.0) -> dict:
    """카카오에서 장소를 찾아 CSV 정보와 대조한다.

    queries: 검색어를 직접 지정 (수동 보정용). 없으면 name_aliases(name)를 차례로 사용.
             ['@주소']를 주면 장소 검색을 건너뛰고 CSV 주소로만 좌표를 찾는다 (오매칭이 반복되는 곳용).
    반환: status(위 STATUS_* 중 하나), lat, lng, place_url, kakao_name, kakao_address, kakao_id,
          name_score, address_match, query, note, candidates(사람 확인용 상위 후보 3개)
    """
    if not rest_key():
        return _empty(STATUS_NO_KEY, 'KAKAO_REST_API_KEY 미설정')

    address_only = queries == [ADDRESS_ONLY]
    want_district = _district(address) or REGION_INFO.get(region, {}).get('district', '')
    seen: dict[str, dict] = {}
    scored = []  # (정렬키, doc, name_score, address_match, query)
    try:
        for query in ([] if address_only else (queries or name_aliases(name))):
            for doc in _keyword_search(query, region):
                doc_id = doc.get('id') or doc.get('place_url') or doc.get('place_name')
                if doc_id in seen:
                    continue
                seen[doc_id] = doc
                district = _district(_doc_address(doc))
                if want_district and district and district != want_district:
                    continue
                ns = name_score(name, doc.get('place_name', ''))
                if queries:  # 수동 검색어를 줬으면 검색어 기준 점수도 인정 (상호가 바뀐 곳 보정용)
                    ns = max(ns, name_score(query, doc.get('place_name', '')))
                am = address_match(address, doc)
                scored.append(((am is True, ns), doc, ns, am, query))
            if pause:
                time.sleep(pause)
            # 이름·주소가 모두 맞는 결과가 나오면 남은 검색어는 생략
            if any(ns >= NAME_THRESHOLD and am is not False for _, _, ns, am, _ in scored):
                break
    except (requests.RequestException, RuntimeError, ValueError) as exc:
        return _empty(STATUS_ERROR, f'키워드 검색 실패: {type(exc).__name__}')

    scored.sort(key=lambda row: row[0], reverse=True)
    candidates = [f"{d.get('place_name', '')} | {_doc_address(d)}" for _, d, *_ in scored[:3]]

    chosen, status, note = None, None, ''
    good_name = [r for r in scored if r[2] >= NAME_THRESHOLD]
    if good_name:
        ok = [r for r in good_name if r[3] is not False]
        if ok:
            # 주소까지 맞는 것 → 이름 점수 순
            ok.sort(key=lambda r: (r[3] is True, r[2]), reverse=True)
            chosen, status = ok[0], STATUS_OK
            if chosen[3] is None:
                note = 'CSV 주소가 모호해 이름·구로만 대조'
        else:
            chosen, status = good_name[0], STATUS_ADDR_DIFF
            note = f'CSV 주소({address})와 카카오 주소가 다름 — 이전·다른 지점인지 확인'
    else:
        same_address = [r for r in scored if r[3] is True]
        if same_address:
            same_address.sort(key=lambda r: r[2], reverse=True)
            chosen, status = same_address[0], STATUS_NAME_DIFF
            note = f"같은 주소의 카카오 장소명이 '{chosen[1].get('place_name', '')}' — 상호 변경·다른 가게인지 확인"

    if chosen:
        doc = chosen[1]
        if not _valid_coords(doc.get('y'), doc.get('x')):
            return _empty(STATUS_ERROR, '카카오 좌표 형식 오류', candidates)
        return {
            'status': status,
            'lat': float(doc['y']), 'lng': float(doc['x']),
            'place_url': doc.get('place_url', ''),
            'kakao_name': doc.get('place_name', ''),
            'kakao_address': _doc_address(doc),
            'kakao_id': str(doc.get('id', '')),
            'name_score': chosen[2], 'address_match': chosen[3], 'query': chosen[4],
            'note': note, 'candidates': candidates,
        }

    # 장소 검색 실패 → 주소 검색으로 좌표라도 확보 (번지가 있는 주소일 때만, '○○ 1 일대'도 포함)
    if _address_keys(address):
        try:
            doc = _address_search(address)
        except (requests.RequestException, RuntimeError, ValueError) as exc:
            return _empty(STATUS_ERROR, f'주소 검색 실패: {type(exc).__name__}', candidates)
        if doc and _valid_coords(doc.get('y'), doc.get('x')):
            road = (doc.get('road_address') or {}).get('address_name') or doc.get('address_name', '')
            note = ('수동 지정(@주소) — CSV 주소로만 좌표 표시' if address_only
                    else '거리·구역 장소 — CSV 대표 지점 주소로 좌표 표시' if is_vague_address(address)
                    else '카카오 장소 검색에 없음 — CSV 주소 위치만 표시 (폐업·미등록 확인)')
            result = _empty(STATUS_ADDR_ONLY, note, candidates)
            result.update({'lat': float(doc['y']), 'lng': float(doc['x']), 'kakao_address': road})
            return result

    return _empty(STATUS_NOT_FOUND, '이름·주소로 찾지 못함 — 정확한 상호명이나 주소 확인 필요', candidates)


@lru_cache(maxsize=256)
def _cached_match(name: str, region: str, address: str) -> dict:
    return match_place(name, region, address)


# ---------------------------------------------------------------------------
# AI 추천 검증 (예전 kakao_verifier.verify_places와 같은 입출력)
# ---------------------------------------------------------------------------
def verify_places(ai_places: list[dict], region: str) -> tuple[list[dict], list[str]]:
    """AI가 추천한 장소 목록 중 카카오에서 확인되는 곳만 남긴다.

    반환: (검증 통과 목록, 제외된 장소 이름 목록)
    통과 기준: 이름이 맞는 결과(일치, 주소 다름). 이름이 다르거나 주소로만 찾은 곳은 제외.
    """
    verified, dropped = [], []
    for place in ai_places:
        name = place.get('name', '')
        result = _cached_match(name, region, place.get('address', '') or '')
        if result['status'] in (STATUS_OK, STATUS_ADDR_DIFF):
            verified.append({
                **place,
                'name': result['kakao_name'],
                'address': result['kakao_address'],
                'lat': result['lat'], 'lng': result['lng'],
                'place_url': result['place_url'],
                'is_verified': True,
                'match_status': result['status'],
            })
        else:
            dropped.append(name)
    return verified, dropped


# ---------------------------------------------------------------------------
# 지도용: CSV 한 행 → 지도 장소 모양
# ---------------------------------------------------------------------------
def resolve_place(place: dict) -> dict:
    """원본 CSV를 변경하지 않고, 지도에 쓸 장소 정보를 생성한다.

    places.csv에 좌표가 채워져 있으면(fill_kakao_coords.py 실행 후) API를 부르지 않는다.
    """
    lat, lng = place.get('latitude'), place.get('longitude')
    csv_status = (place.get('kakao_match_status') or '').strip()
    if _valid_coords(lat, lng):
        status = f'카카오 대조: {csv_status}' if csv_status else 'CSV 좌표 (별도 검증 필요)'
        coords = {'lat': float(lat), 'lng': float(lng), 'status': status,
                  'place_url': place.get('kakao_place_url', '')}
    else:
        found = _cached_match(place.get('name', ''), place.get('region', ''), place.get('address', ''))
        if found['status'] in COORD_STATUSES:
            coords = {'lat': found['lat'], 'lng': found['lng'], 'place_url': found['place_url'],
                      'status': f"카카오 대조: {found['status']} (영업상태 미확인)"}
        else:
            coords = {'lat': None, 'lng': None, 'place_url': '', 'status': found['status']}

    return {
        'place_id': place.get('place_id', ''),
        'name': place.get('name', ''), 'category': place.get('category', ''),
        'address': place.get('address', ''),
        'reason': place.get('ai_reason', ''),
        'lat': coords.get('lat'), 'lng': coords.get('lng'),
        'place_url': coords.get('place_url') or place.get('source_url', ''),
        'location_status': coords.get('status', '좌표 미확인'),
    }


# ---------------------------------------------------------------------------
# 도보 경로
# ---------------------------------------------------------------------------
@lru_cache(maxsize=128)
def _walk_cached(coordinates: tuple[tuple[float, float], ...]) -> dict:
    """각 좌표는 (lat, lng); 카카오 도보 경로 (경유지 최대 5개)."""
    params = {
        'start_x': coordinates[0][1], 'start_y': coordinates[0][0],
        'end_x': coordinates[-1][1], 'end_y': coordinates[-1][0],
        'route_mode': 'SHORTEST',
    }
    if len(coordinates) > 2:
        params['via_x'] = ','.join(str(p[1]) for p in coordinates[1:-1])
        params['via_y'] = ','.join(str(p[0]) for p in coordinates[1:-1])
    try:
        result = _get('/v2/routing/walk', params)
    except (requests.RequestException, RuntimeError, ValueError):
        return {'status': '도보 경로 API 호출 실패'}
    if result.get('status') != 'OK':
        return {'status': f"도보 경로 조회 불가: {result.get('status', '알 수 없는 오류')}"}
    route = result.get('route') or {}
    prop = route.get('properties') or {}
    path = []
    for leg in route.get('legs', []):
        for step in leg.get('steps', []):
            for lng, lat in (step.get('path') or {}).get('points', []):
                if _valid_coords(lat, lng):
                    path.append([float(lat), float(lng)])
    # 지도 HTML이 과도하게 커지지 않게 제한한다 (보행 경로의 주요 점을 유지).
    if len(path) > 1800:
        step = (len(path) - 1) // 1799 + 1
        path = path[::step] + [path[-1]]
    return {
        'status': 'OK',
        'distance_m': prop.get('totalDistance'),
        'duration_s': prop.get('totalTime'),
        'landing_url': prop.get('landingUrl', ''),
        'path': path,
    }


def walking_route(ordered: list[dict]) -> dict:
    if len(ordered) < 2 or len(ordered) > 7:
        return {'status': '도보 경로는 2~7곳 사이로 조회해야 해요.'}
    if not rest_key():
        return {'status': 'KAKAO_REST_API_KEY 미설정'}
    coordinates = tuple((round(float(p['lat']), 7), round(float(p['lng']), 7)) for p in ordered)
    return _walk_cached(coordinates)


if __name__ == '__main__':
    import json
    import sys
    args = sys.argv[1:] or ['서울숲', '성수', '서울특별시 성동구 뚝섬로 273']
    print(json.dumps(match_place(*args[:3]), ensure_ascii=False, indent=2))
