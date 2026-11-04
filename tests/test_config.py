from dataclasses import replace
import json
import pytest
from researchgee.config import Analysis,bbox,from_manifest,validate_geometry

@pytest.fixture
def spec():
    return Analysis('Sentinel-2 SR','2024-01-01','2024-02-01',bbox(90,23,91,24),scale=20)

def test_manifest_roundtrip(spec):
    assert from_manifest(json.loads(json.dumps(spec.manifest()))) == spec
    assert 'project' not in json.dumps(spec.manifest())
    assert spec.fingerprint() != replace(spec,scale=30).fingerprint()

@pytest.mark.parametrize('changes',[{'start':'2024-02-01'},{'scale':0},{'scale':float('nan')},{'crs':'bad'},{'dataset':'invented'},{'reducer':'sum'},{'index':'invented'},{'reducer':'scene'},{'relative_orbit':200}])
def test_invalid_design(spec,changes):
    with pytest.raises(ValueError):
        replace(spec,**changes).validate()

def test_rain_sum(spec):
    replace(spec,dataset='CHIRPS daily rain',reducer='sum').validate()
    with pytest.raises(ValueError):
        replace(spec,dataset='CHIRPS daily rain',index='NDVI').validate()

@pytest.mark.parametrize('bounds',[(91,23,90,24),(90,24,91,23),(-181,0,1,1),(0,0,float('nan'),1)])
def test_bad_bbox(bounds):
    with pytest.raises(ValueError):
        bbox(*bounds)

def test_geojson(spec):
    assert validate_geometry({'type':'Feature','geometry':spec.geometry}) == spec.geometry
    with pytest.raises(ValueError):
        validate_geometry({'type':'Polygon','coordinates':[[[0,0],[1,0],[1,1]]]})
    with pytest.raises(ValueError):
        validate_geometry({'type':'FeatureCollection','features':[]})
