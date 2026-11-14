"""카카오 대조 로직·좌표 채우기 테스트 (네트워크·API 키 없이 가짜 응답으로 실행).

    python -m unittest discover tests
"""
import csv
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import fill_kakao_coords as fill  # noqa: E402
import kakao_service as ks  # noqa: E402


def doc(name, road, jibun='', x='127.04', y='37.54', pid='1'):
    return {'id': pid, 'place_name': name, 'road_address_name': road, 'address_name': jibun or road,
            'x': x, 'y': y, 'place_url': f'http://place.map.kakao.com/{pid}'}


class FakeKakao:
    """검색어 → documents. 주소 검색은 address 키로."""
    def __init__(self, keyword=None, address=None):
        self.keyword, self.address, self.calls = keyword or {}, address or {}, []

    def __call__(self, path, params):
        self.calls.append((path, params['query']))
        if path.endswith('keyword.json'):
            return {'documents': self.keyword.get(params['query'], [])}
        return {'documents': self.address.get(params['query'], [])}


class Base(unittest.TestCase):
    def setUp(self):
        ks._cached_match.cache_clear()
        patcher = mock.patch.object(ks, 'rest_key', return_value='test-key')
        patcher.start()
        self.addCleanup(patcher.stop)

    def fake(self, **kw):
        fake = FakeKakao(**kw)
        patcher = mock.patch.object(ks, '_get', side_effect=fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        return fake


class MatchPlaceTest(Base):
    def test_exact_name_and_address(self):
        self.fake(keyword={'서울숲': [doc('서울숲', '서울 성동구 뚝섬로 273')]})
        r = ks.match_place('서울숲', '성수', '서울특별시 성동구 뚝섬로 273')
        self.assertEqual(r['status'], ks.STATUS_OK)
        self.assertTrue(r['address_match'])
        self.assertTrue(r['place_url'].startswith('http://place.map.kakao.com/'))

    def test_parenthesis_alias_is_searched(self):
        fake = self.fake(keyword={'디뮤지엄': [doc('디뮤지엄', '서울 성동구 왕십리로 83-21')]})
        r = ks.match_place('디뮤지엄 (D MUSEUM)', '성수', '서울특별시 성동구 왕십리로 83-21')
        self.assertEqual(r['status'], ks.STATUS_OK)
        self.assertEqual([q for _, q in fake.calls], ['디뮤지엄 (D MUSEUM)', '디뮤지엄'])  # 찾으면 멈춤

    def test_region_suffix_and_cafe_prefix(self):
        self.fake(keyword={'어니언 성수': [doc('어니언 성수', '서울 성동구 아차산로9길 8')]})
        r = ks.match_place('카페 어니언 성수', '성수', '서울 성동구 아차산로9길 8')
        self.assertEqual(r['status'], ks.STATUS_OK)

    def test_same_address_different_name(self):
        self.fake(keyword={'성수감자탕': [doc('소문난성수감자탕 본점', '서울 성동구 연무장길 45')],
                           '와이덴 성수': [doc('다른가게', '서울 성동구 성수이로 1', '서울 성동구 성수동2가 289-211')]})
        r = ks.match_place('와이덴 성수', '성수', '서울 성동구 성수동2가 289-211')
        self.assertEqual(r['status'], ks.STATUS_NAME_DIFF)
        self.assertIn('다른가게', r['note'])
        self.assertIsNotNone(r['lat'])

    def test_name_matches_but_address_differs(self):
        self.fake(keyword={'오밀 성수': [doc('오밀', '서울 성동구 연무장길 99')]})
        r = ks.match_place('오밀 성수', '성수', '서울 성동구 아차산로5길 37-1')
        self.assertEqual(r['status'], ks.STATUS_ADDR_DIFF)

    def test_other_district_is_ignored(self):
        self.fake(keyword={'서울숲': [doc('서울숲', '서울 강남구 테헤란로 1')]})
        r = ks.match_place('서울숲', '성수', '서울특별시 성동구 뚝섬로 273')
        self.assertNotIn(r['status'], (ks.STATUS_OK, ks.STATUS_ADDR_DIFF))

    def test_address_number_boundary(self):
        self.assertFalse(ks.address_match('서울 성동구 뚝섬로 27', doc('x', '서울 성동구 뚝섬로 273')))
        self.assertTrue(ks.address_match('서울 성동구 뚝섬로 273, 1층', doc('x', '서울 성동구 뚝섬로 273')))

    def test_vague_address_uses_name_only(self):
        self.fake(keyword={'써니볼 (SUNNY BOWL)': [doc('써니볼', '서울 마포구 와우산로 1')]})
        r = ks.match_place('써니볼 (SUNNY BOWL)', '홍대', '서울 마포구 홍대 생활권')
        self.assertEqual(r['status'], ks.STATUS_OK)
        self.assertIsNone(r['address_match'])

    def test_kakao_jibun_only_is_not_address_mismatch(self):
        # 서울숲처럼 카카오에 지번만 있으면 도로명 주소와 비교하지 않는다
        self.fake(keyword={'서울숲': [doc('서울숲', '', '서울 성동구 성수동1가 678-1')]})
        r = ks.match_place('서울숲', '성수', '서울특별시 성동구 뚝섬로 273')
        self.assertEqual(r['status'], ks.STATUS_OK)
        self.assertIsNone(r['address_match'])

    def test_branch_inside_place_is_not_the_place(self):
        self.assertLess(ks.name_score('경의선 책거리', 'GS25 경의선책거리점'), ks.NAME_THRESHOLD)
        self.assertLess(ks.name_score('글로우 성수', '이브닝글로우'), ks.NAME_THRESHOLD)
        self.assertLess(ks.name_score('글로우 성수', '글로우이브닝클럽'), ks.NAME_THRESHOLD)
        self.assertGreaterEqual(ks.name_score('서울숲', '서울숲공원'), ks.NAME_THRESHOLD)

    def test_street_with_number_gets_representative_point(self):
        fake = self.fake(address={'서울특별시 성동구 연무장길 1': [
            {'x': '127.05', 'y': '37.54', 'address_name': '서울 성동구 성수동2가 1', 'road_address': None}]})
        r = ks.match_place('성수 연무장길', '성수', '서울특별시 성동구 연무장길 1 일대')
        self.assertEqual(r['status'], ks.STATUS_ADDR_ONLY)
        self.assertIn('대표 지점', r['note'])
        self.assertIn(('/v2/local/search/address.json', '서울특별시 성동구 연무장길 1'), fake.calls)

    def test_suffix_only_overlap_is_not_a_match(self):
        self.assertLess(ks.name_score('Jincheongyujeom (연남동 한식당)', '한식당'), ks.NAME_THRESHOLD)

    def test_address_only_fallback(self):
        fake = self.fake(address={'서울 성동구 성수이로7길 27': [
            {'x': '127.05', 'y': '37.54', 'address_name': '서울 성동구 성수동2가 1',
             'road_address': {'address_name': '서울 성동구 성수이로7길 27'}}]})
        r = ks.match_place('없는가게', '성수', '서울 성동구 성수이로7길 27 106-2호')
        self.assertEqual(r['status'], ks.STATUS_ADDR_ONLY)
        self.assertEqual(r['place_url'], '')
        self.assertIn(('/v2/local/search/address.json', '서울 성동구 성수이로7길 27'), fake.calls)

    def test_not_found(self):
        self.fake()
        r = ks.match_place('없는가게', '홍대', '서울 마포구 홍대 일대')
        self.assertEqual(r['status'], ks.STATUS_NOT_FOUND)
        self.assertIsNone(r['lat'])

    def test_api_error(self):
        import requests
        with mock.patch.object(ks, '_get', side_effect=requests.Timeout()):
            self.assertEqual(ks.match_place('서울숲', '성수', '')['status'], ks.STATUS_ERROR)

    def test_no_key(self):
        with mock.patch.object(ks, 'rest_key', return_value=''):
            self.assertEqual(ks.match_place('서울숲')['status'], ks.STATUS_NO_KEY)

    def test_override_for_renamed_place(self):
        self.fake(keyword={'소극장산울림': [doc('카페산울림', '서울 마포구 와우산로 157', pid='1'),
                                       doc('소극장산울림', '서울 마포구 와우산로 157', pid='2')]})
        r = ks.match_place('산울림 소극장', '홍대', '서울특별시 마포구 와우산로 157', queries=['소극장산울림'])
        self.assertEqual((r['status'], r['kakao_name']), (ks.STATUS_OK, '소극장산울림'))

    def test_override_address_only(self):
        fake = self.fake(address={'서울 성동구 성수이로16길 32': [
            {'x': '127.05', 'y': '37.54', 'address_name': 'a', 'road_address': {'address_name': '서울 성동구 성수이로16길 32'}}]})
        r = ks.match_place('글로우 성수', '성수', '서울 성동구 성수이로16길 32 3동', queries=[ks.ADDRESS_ONLY])
        self.assertEqual(r['status'], ks.STATUS_ADDR_ONLY)
        self.assertEqual([p for p, _ in fake.calls], ['/v2/local/search/address.json'])

    def test_override_query(self):
        self.fake(keyword={'진정유전': [doc('진정유전', '서울 마포구 동교로46길 27')]})
        r = ks.match_place('Jincheongyujeom (연남동 한식당)', '홍대', '서울특별시 마포구 동교로46길 27',
                           queries=['진정유전'])
        self.assertEqual(r['status'], ks.STATUS_OK)


class CompatTest(Base):
    def test_verify_places_shape(self):
        self.fake(keyword={'대림창고': [doc('대림창고', '서울 성동구 성수이로 78')]})
        verified, dropped = ks.verify_places(
            [{'name': '대림창고', 'reason': 'r'}, {'name': '가짜카페99'}], '성수')
        self.assertEqual(dropped, ['가짜카페99'])
        self.assertEqual(verified[0]['reason'], 'r')
        for key in ('name', 'address', 'lat', 'lng', 'place_url', 'is_verified'):
            self.assertIn(key, verified[0])

    def test_old_import_still_works(self):
        import kakao_verifier
        self.assertIs(kakao_verifier.verify_places, ks.verify_places)

    def test_resolve_place_uses_csv_coords_without_api(self):
        with mock.patch.object(ks, '_get', side_effect=AssertionError('API 호출하면 안 됨')):
            r = ks.resolve_place({'name': '서울숲', 'latitude': '37.5444', 'longitude': '127.0374',
                                  'kakao_match_status': '일치', 'kakao_place_url': 'http://place.map.kakao.com/1'})
        self.assertEqual(r['lat'], 37.5444)
        self.assertEqual(r['place_url'], 'http://place.map.kakao.com/1')


class FillScriptTest(Base):
    def setUp(self):
        super().setUp()
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.places = self.tmp / 'places.csv'
        shutil.copy(fill.PLACES_CSV, self.places)
        with self.places.open(encoding='utf-8-sig', newline='') as fp:
            rows = list(csv.DictReader(fp))
        self.rows = {r['place_id']: r for r in rows}

    def test_fill_preserves_columns_and_writes_report(self):
        p1, p94 = self.rows['P001'], self.rows['P094']
        self.fake(keyword={p1['name']: [doc(p1['name'], '서울 성동구 뚝섬로 273')]})
        _, before = fill.read_csv(self.places)
        old_fields, _ = fill.read_csv(self.places)
        out = fill.run(self.places, self.tmp / 'unmatched.csv', self.tmp / 'none.csv',
                       only={'P001', 'P094'}, pause=0)
        fields, rows = fill.read_csv(self.places)
        self.assertEqual(fields[:len(old_fields)], old_fields)       # 기존 열 순서 유지
        self.assertEqual(len(rows), len(before))                     # 행 수 유지
        by_id = {r['place_id']: r for r in rows}
        self.assertEqual(by_id['P001']['kakao_match_status'], ks.STATUS_OK)
        self.assertTrue(by_id['P001']['latitude'])
        self.assertEqual(by_id['P094']['kakao_match_status'], ks.STATUS_NOT_FOUND)
        self.assertEqual(by_id['P002']['kakao_match_status'], '')    # --only 밖은 그대로
        self.assertEqual(by_id['P002']['tags'], self.rows['P002']['tags'])
        _, review = fill.read_csv(self.tmp / 'unmatched.csv')
        self.assertIn('P094', {r['place_id'] for r in review})
        self.assertNotIn('P001', {r['place_id'] for r in review})
        self.assertEqual(out['looked_up'], 2)
        self.assertTrue(self.places.read_bytes().startswith(b'\xef\xbb\xbf'))  # BOM 유지

    def test_vague_address_replaced_only_on_match(self):
        name = self.rows['P101']['name']
        self.fake(keyword={name: [doc('써니볼', '서울 마포구 와우산로 1')]})
        fill.run(self.places, self.tmp / 'u.csv', self.tmp / 'none.csv', only={'P101'}, pause=0)
        row = {r['place_id']: r for r in fill.read_csv(self.places)[1]}['P101']
        self.assertEqual(row['address'], '서울 마포구 와우산로 1')
        self.assertIn('원래: 서울 마포구 홍대 생활권', row['kakao_match_note'])

    def test_db_tools_still_loads(self):
        import db_tools
        self.fake(keyword={self.rows['P001']['name']: [doc('서울숲', '서울 성동구 뚝섬로 273')]})
        fill.run(self.places, self.tmp / 'u.csv', self.tmp / 'none.csv', only={'P001'}, pause=0)
        detail = db_tools.get_place_detail('P001', db_path=self.places)
        self.assertTrue(detail['found'])
        self.assertTrue(detail['place']['latitude'])


if __name__ == '__main__':
    unittest.main()
