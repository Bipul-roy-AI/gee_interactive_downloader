# Verification record

Date: 2026-11-04. Environment: Python 3.12, Streamlit 1.66.1, earthengine-api 1.7.51, Folium 0.20.0, streamlit-folium 0.27.4, pandas 2.2.3.

## Completed locally

- 30 automated tests passed: manifest round trips; invalid dates, coordinates, scale, CRS, filters and dataset/reducer combinations; EE graph serialization for every temporal dataset; optical masks/scales; index formulas and zero-denominator masking; empty-collection and time-series-limit errors; observation counts/source IDs; terrain construction; download/export parameters; unauthenticated UI; all dataset forms; invalid bounds.
- Python compilation checks passed.
- Actual Streamlit application launched locally. Chromium browser captured Study design and Methods/catalog screens in setup mode; no Google credentials or fabricated satellite results were used.
- README includes access, launch, workflow, benefits, screenshots, limitations, examples, troubleshooting and citations to official documentation.

## Not verified here

No authenticated Earth Engine project was available. Live retrieval, numerical server outputs, map tiles, account task status, direct downloads and Drive export completion have not been verified. The notebook dependency stack has not been exercised in a Jupyter frontend.

Before merging for production/research use:
1. Authenticate a project and run `EE_PROJECT=your-project python scripts/live_smoke.py` (on Windows set the variable using your shell).
2. Compare optical reflectance/index values on a small AOI against the official dataset examples; inspect clouds and valid counts.
3. Check each intended dataset, a single-scene result, the time series, baseline comparison and static terrain.
4. Download a small TIFF and confirm CRS, grid, band values and counts in GIS. Submit a small Drive export and verify completion and output.
5. Archive an authenticated result screenshot with its methods manifest for any claim of live operation.

Automated tests mock server responses where necessary and cannot establish scientific validity of a result. This upgrade is presented as a draft pending the live checks above.
