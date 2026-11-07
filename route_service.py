"""소규모 당일 나들이 동선 추천: 직선거리 기준 순서 탐색 + 카카오 도보 경로 확인.

방문 순서의 목적함수는 직선거리 합계(근사)이며 실제 도보 최적해를 보장하지 않는다.
"""
from itertools import permutations
from math import asin, cos, radians, sin, sqrt


def straight_distance_m(a: dict, b: dict) -> float:
    lat_a, lat_b = radians(float(a['lat'])), radians(float(b['lat']))
    delta_lat = lat_b - lat_a
    delta_lng = radians(float(b['lng']) - float(a['lng']))
    x = sin(delta_lat / 2)**2 + cos(lat_a) * cos(lat_b) * sin(delta_lng / 2)**2
    return 2 * 6371000 * asin(min(1, sqrt(max(0, x))))


def distance_sum(ordered: list[dict] | tuple[dict, ...]) -> float:
    return sum(straight_distance_m(ordered[i], ordered[i + 1]) for i in range(len(ordered) - 1))


def recommend_order(places: list[dict], fixed_start_id: str | None = None) -> dict:
    """2~5개 장소의 최단 '직선거리 합계' 순서를 찾는다 (출발지 미선택 시 첫 장소도 최적화)."""
    if not 2 <= len(places) <= 5:
        raise ValueError('동선 추천은 2~5곳을 선택해 주세요.')
    if len({p['place_id'] for p in places}) != len(places):
        raise ValueError('중복된 장소는 동선에 넣을 수 없어요.')
    if any(p.get('lat') is None or p.get('lng') is None for p in places):
        raise ValueError('좌표가 확인되지 않은 장소가 있어요.')

    if fixed_start_id:
        first = next((p for p in places if p['place_id'] == fixed_start_id), None)
        if first is None:
            raise ValueError('출발 장소가 찜한 장소에 없어요.')
        rest = [p for p in places if p['place_id'] != fixed_start_id]
        choices = ([first, *order] for order in permutations(rest))
    else:
        choices = permutations(places)
    best = min(choices, key=distance_sum)
    return {'ordered': list(best), 'straight_distance_m': round(distance_sum(best))}