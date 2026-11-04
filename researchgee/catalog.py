"""Explicit dataset semantics; output scale is not a claim of native resolution."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Dataset:
    asset: str
    kind: str
    bands: tuple
    scale: int
    units: str
    minimum: float
    maximum: float
    note: str

CATALOG = {
    'Sentinel-2 SR': Dataset('COPERNICUS/S2_SR_HARMONIZED', 's2', ('blue','green','red','nir','swir1','swir2'), 20, 'surface reflectance', 0, .3, '10/20 m source bands; default common output grid 20 m. SCL excludes no-data, saturated, shadow, cloud, cirrus and snow pixels.'),
    'Landsat 8 SR': Dataset('LANDSAT/LC08/C02/T1_L2', 'landsat', ('blue','green','red','nir','swir1','swir2','temperature'), 30, 'reflectance; temperature K', 0, .3, 'QA_PIXEL bits 0–5 and QA_RADSAT masked. Thermal data can be missing; thermal source resolution differs from delivered grid.'),
    'Landsat 9 SR': Dataset('LANDSAT/LC09/C02/T1_L2', 'landsat', ('blue','green','red','nir','swir1','swir2','temperature'), 30, 'reflectance; temperature K', 0, .3, 'Same processing as Landsat 8; no cross-sensor harmonization.'),
    'MODIS surface reflectance': Dataset('MODIS/061/MOD09GA', 'modis', ('blue','green','red','nir','swir1','swir2'), 500, 'surface reflectance', 0, .3, 'state_1km cloud, shadow, cirrus, internal-cloud and snow flags masked. QC_500m rejects non-ideal MODLAND quality; QA is coarser than reflectance.'),
    'Sentinel-1 radar': Dataset('COPERNICUS/S1_GRD', 's1', ('VV','VH'), 10, 'dB', -25, 0, 'IW dual-polarization scenes, one orbit direction. Means/medians are in dB, not linear power. No speckle filter or terrain flattening; match relative orbit for change studies.'),
    'CHIRPS daily rain': Dataset('UCSB-CHG/CHIRPS/DAILY', 'rain', ('precipitation',), 5566, 'mm/day; sum = mm over period', 0, 30, 'Daily gridded precipitation, about 0.05 degrees. Missing days are not filled. Verify temporal coverage before using sums.'),
    'ERA5-Land daily temperature': Dataset('ECMWF/ERA5_LAND/DAILY_AGGR', 'era5', ('temperature_2m',), 11132, 'K', 260, 310, 'Daily mean 2 m air temperature on a coarse reanalysis grid; not land surface temperature.'),
    'SRTM terrain': Dataset('USGS/SRTMGL1_003', 'dem', ('elevation','slope','aspect'), 30, 'elevation m; slope/aspect degrees', 0, 2000, 'Static elevation product; dates and temporal reducer do not apply. Slope/aspect computed on source projection.'),
    'JRC surface water': Dataset('JRC/GSW1_4/GlobalSurfaceWater', 'water', ('occurrence','seasonality','transition','max_extent'), 30, 'occurrence %; seasonality months; other bands categorical', 0, 100, 'Static 1984–2021 summary, not a current flood map. Categorical layers must not be interpreted as continuous measurements.'),
}
INDICES = {
    'NDVI': ('nir','red'), 'NDWI': ('green','nir'),
    'MNDWI': ('green','swir1'), 'NDBI': ('swir1','nir'),
    'NBR': ('nir','swir2'), 'NDMI': ('nir','swir1'),
}
OPTICAL = {'s2','landsat','modis'}
STATIC = {'dem','water'}
