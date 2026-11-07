"""카카오맵 REST API 연동: 좌표 검색과 도보 경로 확인.

REST 키는 서버 환경변수 KAKAO_REST_API_KEY로만 읽으며 코드/HTML에 포함하지 않는다.
카카오 장소 검색 일치는 '등록 정보 확인'이며 영업 상태나 실제 운영의 보증이 아니다.
"""
from __future__ import annotations

from functools import lru_cache
from difflib import SequenceMatcher
import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = 'https://dapi.kakao.com'


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


def _norm(value: str) -> str:
    return re.sub(r'[^\w가-힣]', '', str(value).casefold())


def _district(address: str) -> str:
    hit = re.search(r'(\S+구)\b', str(address))
    return hit.group(1) if hit else ''


def _valid_coords(lat, lng) -> bool:
    try:
        return 33 <= float(lat) <= 39 and 124 <= float(lng) <= 132
    except (TypeError, ValueError):
        return False


@lru_cache(maxsize=256)
def _lookup(name: str, region: str, address: str) -> dict:
    if not rest_key():
        return {'status': '키 없음', 'lat': None, 'lng': None, 'place_url': ''}
    try:
        data = _get('/v2/local/search/keyword.json', {'query': f'{name} {region}', 'size': 10})
    except (requests.RequestException, RuntimeError, ValueError):
        return {'status': '장소 조회 오류', 'lat': None, 'lng': None, 'place_url': ''}

    target = _norm(name)
    aliases = {target, _norm(name.split('(')[0].strip())}
    aliases.discard('')
    csv_district = _district(address)
    matches = []
    for item in data.get('documents', []):
        candidate = _norm(item.get('place_name', ''))
        matched_address = item.get('road_address_name') or item.get('address_name', '')
        district = _district(matched_address)
        if csv_district and district and csv_district != district:
            continue
        # 동일 명칭 또는 충분히 유사한 명칭만 위치로 채택한다.
        similarity = SequenceMatcher(None, target, candidate).ratio()
        if candidate in aliases:
            score = 2.0
        elif len(target) >= 4 and similarity >= 0.84:
            score = similarity
        else:
            continue
        # 동일 구가 확인되면 우선한다. 구가 불분명한 결과는 낮게 취급한다.
        if csv_district and district == csv_district:
            score += 0.15
        matches.append((score, item))

    if not matches:
        return {'status': '장소명·주소 대조 필요', 'lat': None, 'lng': None, 'place_url': ''}
    matches.sort(key=lambda pair: pair[0], reverse=True)
    item = matches[0][1]
    if not _valid_coords(item.get('y'), item.get('x')):
        return {'status': '좌표 확인 필요', 'lat': None, 'lng': None, 'place_url': ''}
    return {
        'status': '카카오 등록 정보 일치 (영업상태 미확인)',
        'lat': float(item['y']), 'lng': float(item['x']),
        'place_url': item.get('place_url', ''),
        'matched_name': item.get('place_name', ''),
        'matched_address': item.get('road_address_name') or item.get('address_name', ''),
    }


def resolve_place(place: dict) -> dict:
    """원본 CSV를 변경하지 않고, 지도에 쓸 장소 정보를 생성한다."""
    lat, lng = place.get('latitude'), place.get('longitude')
    if _valid_coords(lat, lng):
        coords = {'lat': float(lat), 'lng': float(lng), 'status': 'CSV 좌표 (별도 검증 필요)',
                  'place_url': ''}
    else:
        coords = _lookup(place.get('name', ''), place.get('region', ''), place.get('address', ''))

    return {
        'place_id': place.get('place_id', ''),
        'name': place.get('name', ''), 'category': place.get('category', ''),
        'address': place.get('address', ''),
        'reason': place.get('ai_reason', ''),
        'lat': coords.get('lat'), 'lng': coords.get('lng'),
        'place_url': coords.get('place_url') or place.get('source_url', ''),
        'location_status': coords.get('status', '좌표 미확인'),
    }


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