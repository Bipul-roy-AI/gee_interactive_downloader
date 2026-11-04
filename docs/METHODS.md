# Processing methods and limitations

## Optical preprocessing

- Sentinel-2 harmonized surface reflectance: B2/B3/B4/B8/B11/B12 scaled by 0.0001. SCL classes 0, 1, 3, 8, 9, 10 and 11 excluded. SCL is 20 m; B8 and visible bands are 10 m, SWIR 20 m. Default output grid 20 m. No QA60 dependency across its historical availability gap.
- Landsat 8/9 Collection 2 Level 2: SR_B2–SR_B7 × 0.0000275 − 0.2. Exclude QA_PIXEL bits 0–5 and any QA_RADSAT flag. ST_B10 × 0.00341802 + 149 K. Surface temperature is unavailable in L2SR-only scenes; native thermal resolution differs from the delivered 30 m grid. Masking snow means this preset is unsuitable for snow-cover research.
- MODIS MOD09GA v6.1: selected reflectance × 0.0001. Reject non-clear cloud state, shadow, cirrus, internal cloud, snow/ice flags and non-ideal MODLAND quality. This is a conservative basic mask, not a complete aerosol/adjacency or per-band QA workflow; inspect source quality for publication.

Indices are computed for each image before compositing. Normalized differences use explicit (a−b)/(a+b), masking absolute denominators ≤1e−6. This retains valid negative reflectance inputs. EVI uses 2.5(NIR−red)/(NIR+6red−7.5blue+1). Values are not clamped to a nominal range; investigate outliers. Scene properties preserve acquisition time and system index.

## Other products

Sentinel-1 filters IW, VV/VH and one pass direction, with optional relative orbit. Backscatter stays in dB; a mean in dB is not the arithmetic mean of linear power. No additional terrain flattening, speckle filtering or incidence-angle normalization is applied.

CHIRPS sums represent accumulated precipitation over available days. ERA5-Land temperature is air temperature in Kelvin. SRTM and JRC are static products; date controls do not affect them. JRC transition and maximum extent are categorical; continuous means/differences of those codes are generally not scientifically meaningful. Select occurrence or seasonality for quantitative regional analysis.

## Spatial/temporal support

All regional operations and exports use the explicit scale and CRS. Default EE nearest-neighbor resampling is retained; no `bestEffort` coarsening. A composite may have a generic default projection, so explicitly supplied reduction/export grids are essential. Terrain derivatives are calculated before clipping on the SRTM source grid.

Counts refer to unmasked contributing images per band, not independent days; overlapping scenes may double-represent a date. Per-scene regional means have varying valid-pixel footprints, so trends can reflect coverage changes. The time series does not silently truncate: more than 250 scenes requires a narrower query. Interactive builds reject more than 5,000 scenes.

A manifest stores query parameters and result source IDs when built. Replaying re-runs the query; it does not freeze catalog versions or restrict retrieval to archived source IDs. Preserve actual exported rasters for exact reproducibility. AOIs must be valid WGS84 polygons; local checks validate structure/ranges but Earth Engine ultimately validates geometry topology.

## Official references

- [Sentinel-2 SR](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED)
- [Landsat 8 Level 2](https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LC08_C02_T1_L2)
- [Landsat 9 Level 2](https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LC09_C02_T1_L2)
- [MODIS MOD09GA](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD09GA)
- [Sentinel-1 GRD](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S1_GRD)
- [CHIRPS](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY)
- [ERA5-Land daily](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_DAILY_AGGR)
- [SRTM](https://developers.google.com/earth-engine/datasets/catalog/USGS_SRTMGL1_003)
- [JRC surface water](https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_GlobalSurfaceWater)
- [Direct download limits](https://developers.google.com/earth-engine/apidocs/ee-image-getdownloadurl)
- [Image exports](https://developers.google.com/earth-engine/guides/exporting_images)
