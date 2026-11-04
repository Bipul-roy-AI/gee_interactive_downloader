"""Lazy EE graph construction. Importing this module never authenticates."""
import ee
from .config import validate_geometry
from .catalog import CATALOG, INDICES, OPTICAL, STATIC


def initialize(project):
    if not project.strip():
        raise ValueError('Enter your registered Google Cloud project ID.')
    ee.Initialize(project=project.strip())


def prepare(image, kind):
    if kind == 's2':
        scl = image.select('SCL')
        mask = scl.neq(0)
        for code in (1,3,8,9,10,11):
            mask = mask.And(scl.neq(code))
        result = image.select(['B2','B3','B4','B8','B11','B12'], ['blue','green','red','nir','swir1','swir2']).multiply(.0001).updateMask(mask)
    elif kind == 'landsat':
        mask = image.select('QA_PIXEL').bitwiseAnd(63).eq(0).And(image.select('QA_RADSAT').eq(0))
        result = image.select(['SR_B2','SR_B3','SR_B4','SR_B5','SR_B6','SR_B7'], ['blue','green','red','nir','swir1','swir2']).multiply(.0000275).add(-.2)
        result = result.addBands(image.select('ST_B10').multiply(.00341802).add(149).rename('temperature')).updateMask(mask)
    elif kind == 'modis':
        qa = image.select('state_1km')
        mask = qa.bitwiseAnd(3).eq(0).And(qa.bitwiseAnd(1 << 2).eq(0)).And(qa.bitwiseAnd(3 << 8).eq(0)).And(qa.bitwiseAnd((1 << 10)|(1 << 12)|(1 << 15)).eq(0)).And(image.select('QC_500m').bitwiseAnd(3).eq(0))
        result = image.select(['sur_refl_b03','sur_refl_b04','sur_refl_b01','sur_refl_b02','sur_refl_b06','sur_refl_b07'], ['blue','green','red','nir','swir1','swir2']).multiply(.0001).updateMask(mask)
    else:
        return image
    return ee.Image(result.copyProperties(image, ['system:time_start','system:index']))


def add_index(image, name):
    if name == 'None':
        return image
    if name == 'EVI':
        n,r,b = image.select('nir'),image.select('red'),image.select('blue')
        denominator = n.add(r.multiply(6)).subtract(b.multiply(7.5)).add(1)
        out = n.subtract(r).multiply(2.5).divide(denominator).updateMask(denominator.abs().gt(1e-6))
    else:
        a,b = (image.select(x) for x in INDICES[name])
        denominator = a.add(b)
        # Explicit division preserves valid negative reflectance inputs, unlike normalizedDifference.
        out = a.subtract(b).divide(denominator).updateMask(denominator.abs().gt(1e-6))
    return image.addBands(out.rename(name))


def collection(spec):
    spec.validate()
    cfg = CATALOG[spec.dataset]
    roi = ee.Geometry(validate_geometry(spec.geometry))
    if cfg.kind in STATIC:
        raise ValueError('Static products do not have a scene collection.')
    col = ee.ImageCollection(cfg.asset).filterBounds(roi).filterDate(spec.start,spec.end)
    if cfg.kind == 's2':
        col = col.filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE',spec.cloud))
    elif cfg.kind == 'landsat':
        col = col.filter(ee.Filter.lte('CLOUD_COVER',spec.cloud))
    elif cfg.kind == 's1':
        col = col.filter(ee.Filter.eq('instrumentMode','IW')).filter(ee.Filter.eq('resolution_meters',10)).filter(ee.Filter.eq('orbitProperties_pass',spec.orbit))
        for polarization in ('VV','VH'):
            col = col.filter(ee.Filter.listContains('transmitterReceiverPolarisation',polarization))
        if spec.relative_orbit:
            col = col.filter(ee.Filter.eq('relativeOrbitNumber_start',spec.relative_orbit))
    col = col.map(lambda img: add_index(prepare(img,cfg.kind),spec.index))
    bands = list(cfg.bands) + ([spec.index] if spec.index != 'None' else [])
    return col.select(bands).sort('system:time_start')


def inventory(spec, limit=250):
    col = collection(spec)
    total = col.size().getInfo()
    def row(img):
        img = ee.Image(img)
        return ee.Feature(None, {'scene_id':img.get('system:index'),'date':img.date().format('YYYY-MM-dd HH:mm:ss')})
    rows = ee.FeatureCollection(col.limit(limit).toList(limit).map(row)).getInfo()['features']
    return total, [f['properties'] for f in rows]


def build(spec):
    spec.validate()
    cfg = CATALOG[spec.dataset]
    roi = ee.Geometry(validate_geometry(spec.geometry))
    if cfg.kind in STATIC:
        img = ee.Image(cfg.asset)
        if cfg.kind == 'dem':
            img = ee.Terrain.products(img)
        return img.select(list(cfg.bands)).clip(roi), {'scene_count':None,'source_ids':[cfg.asset]}
    col = collection(spec)
    if spec.reducer == 'scene':
        col = col.filter(ee.Filter.eq('system:index',spec.scene_id))
    count = col.size().getInfo()
    if count == 0:
        raise ValueError('No scenes match this AOI, date range and filters. Expand dates or check the scene ID.')
    if count > 5000:
        raise ValueError('More than 5,000 scenes; narrow the dates or AOI.')
    img = ee.Image(col.first()) if spec.reducer == 'scene' else getattr(col,spec.reducer)()
    # Count valid observations independently per band, including the chosen index.
    img = img.addBands(col.count().rename([b+'_count' for b in list(cfg.bands)+([spec.index] if spec.index != 'None' else [])]))
    return img.clip(roi), {'scene_count':count,'source_ids':col.aggregate_array('system:index').getInfo()}


def statistics(image, spec, band):
    if CATALOG[spec.dataset].kind == 'water' and band in ('transition','max_extent'):
        raise ValueError('Categorical water bands support visualization/export only; select occurrence or seasonality for regional statistics.')
    reducer = ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True).combine(ee.Reducer.minMax(),sharedInputs=True).combine(ee.Reducer.count(),sharedInputs=True)
    return image.select(band).reduceRegion(reducer=reducer,geometry=ee.Geometry(validate_geometry(spec.geometry)),scale=spec.scale,crs=spec.crs,maxPixels=10**8,tileScale=4).getInfo()


def time_series(spec, band, limit=250):
    col = collection(spec)
    count = col.size().getInfo()
    if count > limit:
        raise ValueError(f'{count} scenes exceed the interactive limit of {limit}; shorten the period. No silent truncation.')
    def row(item):
        img = ee.Image(item)
        values = img.select(band).reduceRegion(reducer=ee.Reducer.mean().combine(ee.Reducer.count(),sharedInputs=True),geometry=ee.Geometry(validate_geometry(spec.geometry)),scale=spec.scale,crs=spec.crs,maxPixels=10**8,tileScale=4)
        return ee.Feature(None,values).set({'date':img.date().format('YYYY-MM-dd HH:mm:ss'),'scene_id':img.get('system:index')})
    return [f['properties'] for f in ee.FeatureCollection(col.toList(limit).map(row)).getInfo()['features']]


def difference(current, baseline, spec, baseline_spec):
    if (spec.dataset,spec.scale,spec.crs,spec.index) != (baseline_spec.dataset,baseline_spec.scale,baseline_spec.crs,baseline_spec.index):
        raise ValueError('Change analysis requires matching dataset, scale, CRS and index.')
    return current.subtract(baseline)


def download_url(image, spec, bands):
    # EE enforces the 32 MB and 10,000-pixel dimension limits; never silently coarsen.
    return image.select(bands).toFloat().getDownloadURL({'region':ee.Geometry(validate_geometry(spec.geometry)),'scale':spec.scale,'crs':spec.crs,'format':'GEO_TIFF','filePerBand':False})


def export_drive(image, spec, bands, name, folder):
    import re
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',name):
        raise ValueError('Export name must contain 1–80 letters, digits, underscores or hyphens.')
    if not bands:
        raise ValueError('Select at least one output band.')
    task = ee.batch.Export.image.toDrive(image=image.select(bands).toFloat(),description=name,folder=folder or 'GEE_Research',fileNamePrefix=name,region=ee.Geometry(validate_geometry(spec.geometry)),scale=spec.scale,crs=spec.crs,maxPixels=10**10,fileFormat='GeoTIFF',formatOptions={'cloudOptimized':True})
    task.start()
    return task.id
