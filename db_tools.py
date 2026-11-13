"""3번: 장소 CSV용 독립 검색 Tool. Python 표준 라이브러리만 사용.

- 1번 좌표/주소 보강 결과를 받아도 기존 place_id와 스키마만 유지되면 실행 가능
- 2번 설명/태그 보강 파일은 선택 사항. 파일이 없어도 기본 검색 가능
- 가격 미확인 장소는 max_price 제한 시 제외(절대 무료로 처리하지 않음)
- 검수전 태그는 출력에 출처·검수 상태를 명시
- 직접 LLM을 호출하지 않음. 4번 팀원이 TOOL_SCHEMAS/dispatch_tool_call 연동
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
BASE_CSV = ROOT / 'data' / 'places.csv'
ENRICH_CSV = ROOT / 'data' / 'place_enrichment.csv'
VALID_REGIONS = ('성수', '홍대')
CATEGORY_ALIASES = {
    '음식점': {'음식점','맛집'}, '맛집': {'음식점','맛집'},
    '카페': {'카페'}, '전시': {'전시','문화체험'},
    '체험': {'문화체험','전시','팝업스토어'}, '쇼핑': {'쇼핑','소품샵'},
    '소품샵': {'쇼핑','소품샵'}, '공원': {'여가활동','랜드마크'}
}

def _tokens(value: Any) -> list[str]:
    if value is None: return []
    if isinstance(value,str):
        raw = value.replace(',', '|').split('|')
    elif isinstance(value,(list,tuple,set)):
        raw = [str(v) for v in value]
    else:
        raise TypeError('태그/카테고리는 문자열 또는 리스트여야 합니다.')
    return list(dict.fromkeys(str(v).strip() for v in raw if str(v).strip()))

def _get_price(row: dict) -> int | None:
    raw = str(row.get('price_krw','')).strip()
    # CSV에서 가격 확인이 안 됐을 때는 0원으로 계산하지 않는다.
    if raw == '': return None
    try:
        price = int(raw.replace(',',''))
    except ValueError:
        return None
    return price if price >= 0 else None

def load_places(db_path: str | Path | None = None, enrichment_path: str | Path | None = None) -> list[dict]:
    """소스 파일을 건드리지 않고 place_id로 두 CSV 병합. 항상 새 목록 반환."""
    base = Path(db_path) if db_path is not None else BASE_CSV
    extra = Path(enrichment_path) if enrichment_path is not None else ENRICH_CSV
    with base.open(encoding='utf-8-sig',newline='') as fp:
        places = list(csv.DictReader(fp))
    ids = [p.get('place_id','').strip() for p in places]
    if any(not x for x in ids) or len(ids) != len(set(ids)):
        raise ValueError('places.csv의 place_id 누락 또는 중복')
    by_id = {}
    if extra.exists():
        with extra.open(encoding='utf-8-sig',newline='') as fp:
            for enrich in csv.DictReader(fp):
                key = (enrich.get('place_id') or '').strip()
                if not key or key in by_id:
                    raise ValueError('place_enrichment.csv의 place_id 누락 또는 중복')
                by_id[key] = enrich
        unknown = set(by_id) - set(ids)
        if unknown:
            raise ValueError(f'보강 CSV에 없는 place_id가 존재: {sorted(unknown)[:5]}')
    result=[]
    for p in places:
        info = by_id.get(p['place_id'], {})
        combined=dict(p)
        for field in ('short_description','companion_tags','purpose_tags','draft_basis','evidence_source_url',
                      'content_origin','review_status','reviewer','reviewed_at','review_note'):
            combined[field] = info.get(field,'')
        result.append(combined)
    return result

def _display(row: dict, matched: list[str] | None = None) -> dict:
    price = _get_price(row)
    return {
        'place_id':row['place_id'],
        'name':row['name'], 'region':row['region'],'category':row['category'],
        'address':row.get('address',''),
        'price_krw':price, 'price_status':'확인 필요' if price is None else row.get('price_status',''),
        'tags':_tokens(row.get('tags','')),
        'short_description':row.get('short_description',''),
        'companion_tags':_tokens(row.get('companion_tags','')),
        'purpose_tags':_tokens(row.get('purpose_tags','')),
        'matched_tags': matched or [],
        'review_status':row.get('review_status','미기재'),
        'content_origin':row.get('content_origin',''),
        'source_url':row.get('source_url',''),
    }

def search_places(
    region: str | None = None,
    tags: list[str] | str | None = None,
    categories: list[str] | str | None = None,
    max_price: int | None = None,
    companion: str | None = None,
    purpose_tags: list[str] | str | None = None,
    limit: int = 10,
    offset: int = 0,
    tag_match: str = 'any',
    exclude_place_ids: list[str] | None = None,
    *,
    db_path: str | Path | None = None,
    enrichment_path: str | Path | None = None
) -> dict:
    """조건 필터 결과: count=전체 일치 건수, places=limit개만 반환.

    max_price는 **한 장소당** 예산 상한. 가격 미확인 후보는 해당 조건에서 제외.
    목적/동행 태그는 자동 초안일 수 있으므로 review_status도 반환.
    """
    if limit < 1 or limit > 100:
        raise ValueError('limit는 1~100이어야 합니다.')
    if offset < 0: raise ValueError('offset은 0 이상이어야 합니다.')
    if max_price is not None:
        if isinstance(max_price, bool): raise ValueError('max_price는 숫자여야 합니다.')
        try: max_price=int(max_price)
        except (TypeError,ValueError): raise ValueError('max_price는 숫자여야 합니다.') from None
        if max_price < 0: raise ValueError('max_price는 0 이상이어야 합니다.')
    if tag_match not in ('any','all'): raise ValueError("tag_match는 'any' 또는 'all'만 허용합니다.")
    requested_tags=_tokens(tags)
    requested_purposes=_tokens(purpose_tags)
    requested_categories=_tokens(categories)
    requested_companion=(companion or '').strip()
    excluded=set(exclude_place_ids or [])
    stats={'total_loaded':0,'excluded_unknown_price':0,'excluded_unmatched':0}
    matches=[]
    for p in load_places(db_path, enrichment_path):
        stats['total_loaded']+=1
        if p['place_id'] in excluded: continue
        if region and p.get('region') != region: continue
        if requested_categories:
            acceptable=set().union(*(CATEGORY_ALIASES.get(c,{c}) for c in requested_categories))
            if p.get('category') not in acceptable: continue
        if max_price is not None:
            price = _get_price(p)
            if price is None:
                stats['excluded_unknown_price'] += 1
                continue
            if price > max_price: continue
        if requested_companion and requested_companion not in _tokens(p.get('companion_tags','')):
            continue
        p_tags=set(_tokens(p.get('tags','')))
        p_purpose=set(_tokens(p.get('purpose_tags','')))
        searchable=p_tags|p_purpose
        if requested_tags:
            if tag_match=='all' and not all(t in searchable for t in requested_tags):continue
            if tag_match=='any' and not any(t in searchable for t in requested_tags):continue
        if requested_purposes and not all(t in p_purpose for t in requested_purposes): continue
        hits=[t for t in requested_tags+requested_purposes if t in searchable]
        # match priority then place_id ensures deterministic behavior across repeated runs.
        matches.append(((-len(hits),p['place_id']),_display(p,hits)))
    matches.sort(key=lambda pair:pair[0])
    selected=[row for _,row in matches]
    warnings=[]
    if region and region not in VALID_REGIONS:
        warnings.append(f'현재 DB에 지역 {region!r}이(가) 없을 수 있습니다. 보유 지역: {", ".join(VALID_REGIONS)}')
    if max_price is not None:
        warnings.append('가격 미확인 장소는 max_price 필터에서 제외했습니다 (0원 취급 안 함).')
    if requested_companion or requested_purposes:
        warnings.append('동행·목적 태그는 검수 전 자동 초안이 포함될 수 있습니다. review_status를 확인하세요.')
    if not selected:
        warnings.append('일치 장소 없음. 조건을 완화할 때는 사용자에게 알리고 다시 조회하세요.')
    return {
        'count':len(selected), 'returned':len(selected[offset:offset+limit]),
        'places':selected[offset:offset+limit],
        'filters':{'region':region,'tags':requested_tags,'categories':requested_categories,
                   'max_price_per_place_krw':max_price,'companion':requested_companion,
                   'purpose_tags':requested_purposes,'tag_match':tag_match,
                   'exclude_place_ids':sorted(excluded),'offset':offset,'limit':limit},
        'stats':stats, 'warnings':warnings,
    }

def get_place_detail(place_id: str, *, db_path: str | Path | None = None,
                     enrichment_path: str | Path | None = None) -> dict:
    for p in load_places(db_path, enrichment_path):
        if p.get('place_id') == place_id:
            res=_display(p)
            res.update({k:p.get(k,'') for k in ('latitude','longitude','opening_hours',
                        'verified_at','data_status','duration_min','reviewer','reviewed_at',
                        'review_note','evidence_source_url','draft_basis')})
            return {'found':True,'place':res}
    return {'found':False,'place':None,'message':f'등록되지 않은 place_id: {place_id}'}

# 4번 LLM 담당자에게 그대로 전달 가능한 OpenAI 호환 Tool schema.
TOOL_SCHEMAS = [
    {'type':'function','function':{
        'name':'search_places','description':'현재 보유한 장소 DB에서 조건에 맞는 장소 후보와 개수를 검색. 장소를 생성하지 않음.',
        'parameters':{'type':'object','properties':{
            'region':{'type':'string','description':'DB 등록 지역(성수 또는 홍대)'},
            'tags':{'type':'array','items':{'type':'string'},'description':'기존 태그 또는 목적 태그'},
            'categories':{'type':'array','items':{'type':'string'}},
            'max_price':{'type':'integer','minimum':0,'description':'장소 1곳당 최대 예산(원)'},
            'companion':{'type':'string','enum':['혼자','친구','연인','가족']},
            'purpose_tags':{'type':'array','items':{'type':'string'}},
            'limit':{'type':'integer','minimum':1,'maximum':100},
        },'additionalProperties':False}}},
    {'type':'function','function':{
        'name':'get_place_detail','description':'실제 DB에 존재하는 place_id로 상세 장소 정보를 조회',
        'parameters':{'type':'object','properties':{'place_id':{'type':'string'}},
                      'required':['place_id'],'additionalProperties':False}}}
]

def dispatch_tool_call(name: str, arguments: str | dict) -> dict:
    """4번 담당자가 LLM tool-call 결과를 수신한 후 실행하도록 만든 연결점."""
    if name not in ('search_places','get_place_detail'):
        return {'error':f'허용되지 않은 툴 이름: {name}'}
    try:
        params=json.loads(arguments) if isinstance(arguments,str) else arguments
        if not isinstance(params,dict):raise ValueError('인자는 JSON 객체여야 합니다.')
        exposed_search = {'region','tags','categories','max_price','companion','purpose_tags','limit'}
        exposed_detail = {'place_id'}
        allowed = exposed_search if name=='search_places' else exposed_detail
        unexpected = set(params)-allowed
        if unexpected:
            raise ValueError('허용되지 않은 인자: '+', '.join(sorted(unexpected)))
        return search_places(**params) if name=='search_places' else get_place_detail(**params)
    except (ValueError,TypeError,KeyError) as e:
        return {'error':str(e)}

if __name__=='__main__':
    print(json.dumps(search_places(region='성수',tags=['산책'],limit=3),ensure_ascii=False,indent=2))
