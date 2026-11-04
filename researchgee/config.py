"""Pure validation and portable analysis manifests (no credentials)."""
from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
import math
from .catalog import CATALOG, INDICES, OPTICAL, STATIC


def validate_geometry(value):
    if not isinstance(value, dict):
        raise ValueError('AOI must be a GeoJSON object.')
    if value.get('type') == 'Feature':
        value = value.get('geometry')
    if not isinstance(value, dict) or value.get('type') not in ('Polygon','MultiPolygon'):
        raise ValueError('Use a WGS84 Polygon or MultiPolygon GeoJSON geometry/feature.')
    polygons = [value.get('coordinates')] if value['type'] == 'Polygon' else value.get('coordinates')
    if not isinstance(polygons, list) or not polygons:
        raise ValueError('AOI coordinates are empty.')
    vertices = 0
    for polygon in polygons:
        if not isinstance(polygon, list) or not polygon:
            raise ValueError('Polygon needs at least one ring.')
        for ring in polygon:
            if not isinstance(ring, list) or len(ring) < 4 or ring[0] != ring[-1]:
                raise ValueError('Every ring needs at least four positions and must be closed.')
            for point in ring:
                if not isinstance(point, (list,tuple)) or len(point) != 2:
                    raise ValueError('Use 2D longitude/latitude coordinates.')
                x,y = point
                if any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) for v in point) or not (-180 <= x <= 180 and -90 <= y <= 90):
                    raise ValueError('Coordinates must be finite WGS84 longitude/latitude.')
                vertices += 1
            if len(set(map(tuple,ring))) < 3:
                raise ValueError('Degenerate polygon ring.')
    if vertices > 10000:
        raise ValueError('Simplify the AOI to at most 10,000 vertices.')
    return value


def bbox(west,south,east,north):
    if not west < east or not south < north:
        raise ValueError('Bounds require west < east and south < north; split antimeridian AOIs.')
    return validate_geometry({'type':'Polygon','coordinates':[[[west,south],[east,south],[east,north],[west,north],[west,south]]]})

@dataclass(frozen=True)
class Analysis:
    dataset: str
    start: str
    end: str
    geometry: dict
    reducer: str = 'median'
    scale: float = 30
    crs: str = 'EPSG:4326'
    index: str = 'None'
    cloud: int = 80
    orbit: str = 'DESCENDING'
    relative_orbit: int = 0
    scene_id: str = ''

    def validate(self):
        if self.dataset not in CATALOG:
            raise ValueError('Unknown dataset.')
        cfg = CATALOG[self.dataset]
        if date.fromisoformat(self.start) >= date.fromisoformat(self.end):
            raise ValueError('Start must precede the exclusive end date.')
        validate_geometry(self.geometry)
        if not math.isfinite(self.scale) or not 1 <= self.scale <= 100000:
            raise ValueError('Scale must be 1–100,000 metres.')
        if not self.crs.startswith('EPSG:') or not self.crs[5:].isdigit():
            raise ValueError('Use an EPSG code, for example EPSG:32646.')
        if self.reducer not in ('median','mean','min','max','sum','scene'):
            raise ValueError('Unsupported reducer.')
        if self.reducer == 'sum' and cfg.kind != 'rain':
            raise ValueError('Sum is supported only for daily precipitation.')
        if self.reducer == 'scene' and not self.scene_id.strip():
            raise ValueError('Choose a scene ID from the inventory first.')
        if self.index != 'None' and (self.index not in (*INDICES,'EVI') or cfg.kind not in OPTICAL):
            raise ValueError('Index is not supported for this dataset.')
        if not 0 <= self.cloud <= 100 or self.orbit not in ('ASCENDING','DESCENDING') or not 0 <= self.relative_orbit <= 175:
            raise ValueError('Invalid cloud/orbit filter.')
        return self

    def manifest(self):
        self.validate()
        return {'schema_version':1,'software_version':'2.0.0','parameters':asdict(self),
                'asset':CATALOG[self.dataset].asset,'end_date_exclusive':True,
                'processing_note':CATALOG[self.dataset].note,
                'temporal_operation':'static' if CATALOG[self.dataset].kind in STATIC else self.reducer}

    def fingerprint(self):
        return hashlib.sha256(json.dumps(self.manifest(),sort_keys=True).encode()).hexdigest()[:16]


def from_manifest(value):
    if value.get('schema_version') != 1:
        raise ValueError('Unsupported manifest version.')
    return Analysis(**value['parameters']).validate()
