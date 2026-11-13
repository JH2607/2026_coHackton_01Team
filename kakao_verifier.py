"""[호환용] 카카오 검증 함수는 kakao_service.py로 통합되었습니다.

새 코드에서는 `from kakao_service import verify_places, match_place`를 사용하세요.
기존 `from kakao_verifier import verify_places` 코드가 깨지지 않도록 남겨 둔 파일이며,
다른 브랜치에서 이 import를 쓰는 곳이 없어지면 삭제해도 됩니다.
"""
from kakao_service import match_place, verify_places  # noqa: F401


def search_place_on_kakao(place_name: str, region: str) -> dict | None:
    """예전 함수 이름 호환: 이름이 맞는 결과가 있을 때만 반환."""
    result = match_place(place_name, region)
    if result['status'] not in ('일치', '주소 다름'):
        return None
    return {'verified_name': result['kakao_name'], 'address': result['kakao_address'],
            'lat': result['lat'], 'lng': result['lng'], 'place_url': result['place_url']}
