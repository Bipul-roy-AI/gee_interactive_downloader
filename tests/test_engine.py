"""Offline EE graph and numerical regressions; no live backend assertions."""
from unittest.mock import patch
import json
import ee
from ee.apitestcase import ApiTestCase
from researchgee import engine
from researchgee.catalog import CATALOG,STATIC
from researchgee.config import Analysis,bbox

class TestGraphs(ApiTestCase):
    def spec(self,name='Sentinel-2 SR',**kwargs):
        return Analysis(name,'2024-01-01','2024-02-01',bbox(90,23,91,24),**kwargs)

    def test_all_collections_serialize(self):
        for name,cfg in CATALOG.items():
            if cfg.kind not in STATIC:
                graph = engine.collection(self.spec(name)).serialize()
                assert cfg.asset in graph
                assert 'system:time_start' in graph

    def test_s2_qa_and_scale(self):
        graph = engine.prepare(ee.Image('test'),'s2').serialize()
        assert 'SCL' in graph and '0.0001' in graph
        assert 'QA60' not in graph

    def test_landsat_masks_and_scale(self):
        graph = engine.prepare(ee.Image('test'),'landsat').serialize()
        for value in ('QA_PIXEL','QA_RADSAT','63','149','0.00341802'):
            assert value in graph

    def test_indices_keep_negative_reflectance(self):
        for index in (*engine.INDICES,'EVI'):
            graph = engine.add_index(ee.Image('test'),index).serialize()
            assert 'Image.normalizedDifference' not in graph
            assert 'Image.divide' in graph and 'Image.updateMask' in graph

    def test_empty_collection_rejected(self):
        with patch.object(ee.Number,'getInfo',return_value=0):
            with self.assertRaisesRegex(ValueError,'No scenes'):
                engine.build(self.spec())

    def test_series_limit_rejects_instead_of_truncating(self):
        with patch.object(ee.Number,'getInfo',return_value=251):
            with self.assertRaisesRegex(ValueError,'No silent truncation'):
                engine.time_series(self.spec(),'red')

    def test_build_counts_and_sources(self):
        with patch.object(ee.Number,'getInfo',return_value=2),patch.object(ee.List,'getInfo',return_value=['scene1','scene2']):
            image,meta = engine.build(self.spec(index='NDVI'))
            graph = image.serialize()
            assert 'NDVI_count' in graph
            assert meta['source_ids'] == ['scene1','scene2']

    def test_static_terrain(self):
        image,meta = engine.build(self.spec('SRTM terrain'))
        assert 'Terrain.products' in image.serialize()
        assert meta['scene_count'] is None

    def test_download_parameters(self):
        with patch.object(ee.Image,'getDownloadURL',return_value='test-url') as call:
            engine.download_url(ee.Image('test'),self.spec(scale=20,crs='EPSG:32646'),['red'])
            params = call.call_args.args[0]
            assert params['scale'] == 20 and params['crs'] == 'EPSG:32646'

    def test_export_explicit_start(self):
        with patch.object(ee.batch.Export.image,'toDrive') as export:
            task = export.return_value
            task.id = 'test-task'
            assert engine.export_drive(ee.Image('test'),self.spec(),['red'],'study_01','Research') == 'test-task'
            task.start.assert_called_once()
            assert export.call_args.kwargs['formatOptions'] == {'cloudOptimized':True}

class ScalarImage:
    """Tiny arithmetic stand-in to test index formulas on known reflectances."""
    def __init__(self,values,valid=True):
        self.values = values if isinstance(values,dict) else {'value':values}
        self.valid = valid
    def select(self,name): return ScalarImage(self.values[name],self.valid)
    def number(self,other): return next(iter(other.values.values())) if isinstance(other,ScalarImage) else other
    def calc(self,other,op): return ScalarImage(op(self.number(self),self.number(other)),self.valid)
    def add(self,x): return self.calc(x,lambda a,b:a+b)
    def subtract(self,x): return self.calc(x,lambda a,b:a-b)
    def multiply(self,x): return self.calc(x,lambda a,b:a*b)
    def divide(self,x): return self.calc(x,lambda a,b:a/b if b else 0)
    def abs(self): return ScalarImage(abs(self.number(self)),self.valid)
    def gt(self,x): return self.number(self)>x
    def updateMask(self,mask): return ScalarImage(self.values,self.valid and mask)
    def rename(self,name): return ScalarImage({name:self.number(self)},self.valid)
    def addBands(self,other): return ScalarImage(self.values|other.values,other.valid)


def test_index_numerical_reference():
    import pytest
    image = ScalarImage({'nir':.6,'red':.2,'blue':.1,'green':.3,'swir1':.4,'swir2':.5})
    assert engine.add_index(image,'NDVI').values['NDVI'] == pytest.approx(.5)
    assert engine.add_index(image,'EVI').values['EVI'] == pytest.approx(1/2.05)
    negative = ScalarImage({'nir':.2,'red':-.1})
    assert engine.add_index(negative,'NDVI').values['NDVI'] == pytest.approx(3)
    assert not engine.add_index(ScalarImage({'nir':.1,'red':-.1}),'NDVI').valid
