"""python -m unittest -v test_db_tools.py  (API 키/인터넷 불필요)"""
import csv
import tempfile
import unittest
from pathlib import Path
from db_tools import search_places, get_place_detail, load_places, dispatch_tool_call, TOOL_SCHEMAS, ROOT

class SearchTests(unittest.TestCase):
    def test_104_id_unique(self):
        rows=load_places()
        self.assertEqual(104,len(rows))
        self.assertEqual(104,len({p['place_id'] for p in rows}))

    def test_search_region(self):
        res=search_places(region='성수', limit=100)
        self.assertEqual(res['count'],50)
        self.assertEqual(len(res['places']),50)
        self.assertTrue(all(p['region']=='성수' for p in res['places']))

    def test_category_alias(self):
        r=search_places(region='홍대', categories=['음식점'],limit=100)
        self.assertGreater(r['count'],0)
        self.assertTrue(all(x['category'] in ('음식점','맛집') for x in r['places']))

    def test_unknown_price_not_free(self):
        r=search_places(region='성수',max_price=0,limit=100)
        self.assertTrue(any(p['place_id']=='P001' for p in r['places']))
        self.assertTrue(all(p['price_krw']==0 for p in r['places']))

    def test_tag_companion_and_purpose(self):
        r=search_places(region='성수',tags=['산책'],companion='연인')
        self.assertIn('P001',[x['place_id'] for x in r['places']])
        r2=search_places(region='성수',purpose_tags=['비오는날'])
        self.assertTrue(all('비오는날' in x['purpose_tags'] for x in r2['places']))

    def test_limit_count(self):
        r=search_places(limit=3)
        self.assertEqual(r['count'],104)
        self.assertEqual(r['returned'],3)

    def test_unknown_region(self):
        r=search_places(region='제주')
        self.assertEqual(0,r['count'])
        self.assertTrue(r['warnings'])

    def test_detail_and_notfound(self):
        p=get_place_detail('P001')
        self.assertTrue(p['found'])
        self.assertEqual(p['place']['name'],'서울숲')
        self.assertFalse(get_place_detail('P999')['found'])

    def test_missing_enrichment_works(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'does-not-exist.csv'
            r=search_places(region='성수',enrichment_path=path)
            self.assertGreater(r['count'],0)
            self.assertEqual(r['places'][0]['short_description'],'')

    def test_no_hallucinated_place_id(self):
        ids={p['place_id'] for p in load_places()}
        r=search_places(tags=['비오는날'])
        self.assertTrue(all(p['place_id'] in ids for p in r['places']))

    def test_dispatch_security(self):
        self.assertIn('error', dispatch_tool_call('invalid',{}))
        self.assertIn('error', dispatch_tool_call('search_places',{'db_path':'/etc/passwd'}))
        self.assertEqual(dispatch_tool_call('get_place_detail','{"place_id":"P001"}')['found'],True)

    def test_json_tool_schemas(self):
        self.assertEqual([s['function']['name'] for s in TOOL_SCHEMAS], ['search_places','get_place_detail'])

if __name__=='__main__':unittest.main()
