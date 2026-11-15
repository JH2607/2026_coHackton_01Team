"""1번: places.csv 좌표·주소·카카오맵 링크 일괄 채우기.

사용법 (프로젝트 폴더에서, .env에 KAKAO_REST_API_KEY 필요)
    python fill_kakao_coords.py                # 아직 '일치'가 아닌 곳만 조회해서 places.csv 갱신
    python fill_kakao_coords.py --dry-run      # 파일은 그대로 두고 결과만 출력
    python fill_kakao_coords.py --all          # 104곳 전부 다시 조회
    python fill_kakao_coords.py --only P030,P094

결과
    data/places.csv          latitude, longitude 채움 + 아래 카카오 열 추가 (기존 열·순서는 그대로)
        kakao_place_name     카카오에 등록된 장소명
        kakao_address        카카오 도로명(없으면 지번) 주소
        kakao_place_url      카카오맵 링크 (주소로만 찾은 곳은 비어 있음)
        kakao_match_status   일치 / 이름 다름 / 주소 다름 / 주소로만 좌표 / 검색 안 됨 / 조회 오류
        kakao_match_note     사람이 확인할 내용
        kakao_checked_at     조회 날짜
    data/kakao_unmatched.csv '일치'가 아닌 곳 목록 (상위 후보 3개 포함) → 사람이 확인

address 열은 원래 값이 '홍대 일대'처럼 번지가 없을 때만, 그리고 '일치'일 때만 카카오 주소로 바꾼다.

수동 보정: 이름이 바뀐 곳 등은 data/kakao_overrides.csv 에
    place_id,query,note
    P030,진청유점,카카오 등록명이 한글
    P062,@주소,장소 검색 없이 CSV 주소로만 좌표 (오매칭이 반복될 때)
처럼 적고 `--only P030`으로 다시 실행하면 그 검색어로 조회한다.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
from pathlib import Path
import tempfile

import kakao_service as ks

ROOT = Path(__file__).resolve().parent
PLACES_CSV = ROOT / 'data' / 'places.csv'
UNMATCHED_CSV = ROOT / 'data' / 'kakao_unmatched.csv'
OVERRIDES_CSV = ROOT / 'data' / 'kakao_overrides.csv'

KAKAO_COLUMNS = ['kakao_place_name', 'kakao_address', 'kakao_place_url',
                 'kakao_match_status', 'kakao_match_note', 'kakao_checked_at']
UNMATCHED_COLUMNS = ['place_id', 'name', 'region', 'csv_address', 'kakao_match_status',
                     'kakao_place_name', 'kakao_address', 'kakao_place_url', 'name_score',
                     'kakao_match_note', 'candidates_top3', 'latitude', 'longitude']


def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(encoding='utf-8-sig', newline='') as fp:
        reader = csv.DictReader(fp)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    """중간에 멈춰도 원본이 깨지지 않도록 임시 파일에 쓴 뒤 교체한다. (원본과 같은 UTF-8 BOM)"""
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    with os.fdopen(fd, 'w', encoding='utf-8-sig', newline='') as fp:
        writer = csv.DictWriter(fp, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def load_overrides(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    _, rows = read_csv(path)
    out: dict[str, list[str]] = {}
    for row in rows:
        pid, query = (row.get('place_id') or '').strip(), (row.get('query') or '').strip()
        if pid and query:
            out.setdefault(pid, []).append(query)
    return out


def apply_result(row: dict, result: dict, today: str) -> None:
    """조회 결과를 CSV 한 행에 반영한다."""
    status = result['status']
    if status == ks.STATUS_NO_KEY:
        raise SystemExit('KAKAO_REST_API_KEY가 없습니다. .env를 확인해 주세요.')
    if status == ks.STATUS_ERROR:
        # 일시 오류일 수 있으므로 기존 좌표는 건드리지 않고 상태만 남긴다.
        row.update({'kakao_match_status': status, 'kakao_match_note': result['note'],
                    'kakao_checked_at': today})
        return
    has_coords = status in ks.COORD_STATUSES
    row['latitude'] = f"{result['lat']:.7f}" if has_coords else ''
    row['longitude'] = f"{result['lng']:.7f}" if has_coords else ''
    row.update({
        'kakao_place_name': result['kakao_name'],
        'kakao_address': result['kakao_address'],
        'kakao_place_url': result['place_url'],
        'kakao_match_status': status,
        'kakao_match_note': result['note'],
        'kakao_checked_at': today,
    })
    if status == ks.STATUS_OK and result['kakao_address'] and ks.is_vague_address(row.get('address', '')):
        before = row.get('address', '')
        row['address'] = result['kakao_address']
        row['kakao_match_note'] = '; '.join(filter(None, [row['kakao_match_note'],
                                                           f"주소 보정 (원래: {before})"]))


def unmatched_row(row: dict, result: dict | None) -> dict:
    return {
        'place_id': row['place_id'], 'name': row['name'], 'region': row['region'],
        'csv_address': row.get('address', ''),
        'kakao_match_status': row.get('kakao_match_status', ''),
        'kakao_place_name': row.get('kakao_place_name', ''),
        'kakao_address': row.get('kakao_address', ''),
        'kakao_place_url': row.get('kakao_place_url', ''),
        'name_score': result['name_score'] if result else '',
        'kakao_match_note': row.get('kakao_match_note', ''),
        'candidates_top3': ' / '.join(result['candidates']) if result else '',
        'latitude': row.get('latitude', ''), 'longitude': row.get('longitude', ''),
    }


def needs_lookup(row: dict, recheck_all: bool, only: set[str]) -> bool:
    if only:
        return row['place_id'] in only
    if recheck_all:
        return True
    done = row.get('kakao_match_status') == ks.STATUS_OK and ks._valid_coords(row.get('latitude'),
                                                                               row.get('longitude'))
    return not done


def run(places_path: Path = PLACES_CSV, unmatched_path: Path = UNMATCHED_CSV,
        overrides_path: Path = OVERRIDES_CSV, *, recheck_all: bool = False,
        only: set[str] | None = None, dry_run: bool = False, pause: float = 0.05) -> dict:
    fields, rows = read_csv(places_path)
    fields += [c for c in KAKAO_COLUMNS if c not in fields]
    overrides = load_overrides(overrides_path)
    today = dt.date.today().isoformat()
    only = only or set()

    results: dict[str, dict] = {}
    for i, row in enumerate(rows, 1):
        for col in KAKAO_COLUMNS:
            row.setdefault(col, '')
        if not needs_lookup(row, recheck_all, only):
            continue
        result = ks.match_place(row['name'], row['region'], row.get('address', ''),
                                queries=overrides.get(row['place_id']), pause=pause)
        apply_result(row, result, today)
        results[row['place_id']] = result
        print(f"[{i:3}/{len(rows)}] {row['place_id']} {row['name']:<28} → {row['kakao_match_status']}"
              f"{'  (' + row['kakao_place_name'] + ')' if row['kakao_place_name'] else ''}")

    # '일치'가 아닌 곳 전체 목록 (이번에 조회 안 한 행도 이전 결과 기준으로 포함)
    review = [unmatched_row(r, results.get(r['place_id'])) for r in rows
              if r.get('kakao_match_status') != ks.STATUS_OK]
    counts: dict[str, int] = {}
    for r in rows:
        key = r.get('kakao_match_status') or '미조회'
        counts[key] = counts.get(key, 0) + 1

    if not dry_run:
        write_csv(places_path, fields, rows)
        write_csv(unmatched_path, UNMATCHED_COLUMNS, review)
    print('\n=== 요약 ===')
    for key, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f'  {key}: {n}곳')
    print(f"  좌표 있음: {sum(ks._valid_coords(r.get('latitude'), r.get('longitude')) for r in rows)}"
          f"/{len(rows)}곳")
    if not dry_run:
        print(f'  확인 필요 목록: {unmatched_path.relative_to(ROOT) if unmatched_path.is_relative_to(ROOT) else unmatched_path}'
              f' ({len(review)}곳)')
    else:
        print('  (--dry-run: 파일은 바꾸지 않았어요)')
    return {'counts': counts, 'review': review, 'looked_up': len(results)}


def main() -> None:
    parser = argparse.ArgumentParser(description='places.csv 카카오 좌표 채우기')
    parser.add_argument('--all', action='store_true', help='이미 일치한 곳까지 전부 다시 조회')
    parser.add_argument('--only', default='', help='쉼표로 구분한 place_id만 조회 (예: P030,P094)')
    parser.add_argument('--dry-run', action='store_true', help='파일을 바꾸지 않고 결과만 출력')
    args = parser.parse_args()
    if not ks.rest_key():
        raise SystemExit('KAKAO_REST_API_KEY가 없습니다. .env를 확인해 주세요.')
    only = {x.strip() for x in args.only.split(',') if x.strip()}
    run(recheck_all=args.all, only=only, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
