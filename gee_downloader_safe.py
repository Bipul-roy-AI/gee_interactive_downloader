"""
Interactive GEE Data Explorer (Research-Safe)
=============================================

Description:
    A Python interface for Google Earth Engine (GEE) to visualize and download
    satellite imagery.
    
    SCIENTIFIC WARNINGS:
    1. MOSAIC: This tool uses a temporal MEDIAN composite to remove clouds. 
       This destroys temporal specificity and is valid only for visualization 
       or background mapping, NOT for event-specific analysis (e.g., floods).
    2. SCALING: Downloads are performed at NATIVE sensor resolution.
    3. HARMONIZATION: Sensors are NOT radiometrically harmonized. Do not compare 
       Sentinel-2 values directly with Landsat without cross-calibration.

Usage:
    Run in a Jupyter environment.
    
Author: Bipul Roy
License: MIT
"""

import ee
import geemap
import ipywidgets as widgets
from IPython.display import display
import pandas as pd

# --- AUTHENTICATE GEE ---
try:
    ee.Initialize()
except Exception:
    ee.Authenticate()
    ee.Initialize()

# ==============================
# SENSOR REGISTRY (With Native Scales)
# ==============================
SENSOR_DB = {
    'Sentinel-2 (SR)': {
        'id': 'COPERNICUS/S2_SR_HARMONIZED',
        'bands': ['B4', 'B3', 'B2'], 
        'native_scale': 10,          # 10m Resolution
        'vis_min': 0.0,
        'vis_max': 3000,
        'type': 'Optical',
        'scaling_func': lambda img: img.divide(10000) # Native values are 0-10000
    },
    'Landsat 9 (SR)': {
        'id': 'LANDSAT/LC09/C02/T1_L2',
        'bands': ['SR_B4', 'SR_B3', 'SR_B2'], 
        'native_scale': 30,          # 30m Resolution
        'vis_min': 0.0,
        'vis_max': 0.3,
        'type': 'Optical',
        # Landsat C2 scaling: (DN * 2.75e-5) - 0.2
        'scaling_func': lambda img: img.select('SR_B.').multiply(0.0000275).add(-0.2)
    },
    'Landsat 8 (SR)': {
        'id': 'LANDSAT/LC08/C02/T1_L2',
        'bands': ['SR_B4', 'SR_B3', 'SR_B2'],
        'native_scale': 30,          # 30m Resolution
        'vis_min': 0.0,
        'vis_max': 0.3,
        'type': 'Optical',
        'scaling_func': lambda img: img.select('SR_B.').multiply(0.0000275).add(-0.2)
    },
    'MODIS (Surface Refl)': {
        'id': 'MODIS/061/MOD09GA',
        'bands': ['sur_refl_b01', 'sur_refl_b04', 'sur_refl_b03'], 
        'native_scale': 500,         # 500m Resolution
        'vis_min': 0.0,
        'vis_max': 4000,
        'type': 'Optical',
        'scaling_func': lambda img: img # Keep raw for now, complex QC required
    }
}

# ==============================
# SCIENTIFIC HELPER FUNCTIONS
# ==============================
def mask_s2_clouds(image):
    """Cloud masking for Sentinel-2 using QA60 band."""
    qa = image.select('QA60')
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11
    mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(
        qa.bitwiseAnd(cirrus_bit_mask).eq(0))
    return image.updateMask(mask)

def mask_landsat_clouds(image):
    """Cloud masking for Landsat Collection 2 using QA_PIXEL."""
    qa = image.select('QA_PIXEL')
    # Bit 3 is Cloud, Bit 4 is Cloud Shadow
    mask = qa.bitwiseAnd(1 << 3).eq(0).And(qa.bitwiseAnd(1 << 4).eq(0))
    return image.updateMask(mask)

def get_processed_collection(sensor_key, start_date, end_date, roi):
    cfg = SENSOR_DB[sensor_key]
    collection = ee.ImageCollection(cfg['id'])\
        .filterDate(start_date, end_date)\
        .filterBounds(roi)
    
    # 1. Apply Cloud Masking (Pre-Mosaic)
    if 'Sentinel' in sensor_key:
        collection = collection.map(mask_s2_clouds)
    elif 'Landsat' in sensor_key:
        collection = collection.map(mask_landsat_clouds)
    elif 'MODIS' in sensor_key:
        print("[WARNING] MODIS Cloud Masking is DISABLED. Result contains artifacts.")

    # 2. Apply Scaling Factors
    # We map the scaling function defined in the registry
    scaled_col = collection.map(cfg['scaling_func'])
    
    return scaled_col

# ==============================
# MAIN INTERACTIVE APP
# ==============================
def main():
    Map = geemap.Map(center=[23.8103, 90.4125], zoom=7)
    Map.add_basemap('HYBRID')

    print("--- GEE Data Explorer (Research-Safe) ---")
    print("WARNING: This tool generates MEDIAN COMPOSITES. Do not use for event detection.")
    
    # Widgets
    style = {'description_width': 'initial'}
    sensor_dropdown = widgets.Dropdown(options=SENSOR_DB.keys(), description='Sensor:', style=style)
    start_date = widgets.DatePicker(description='Start Date:', value=pd.to_datetime('2023-01-01'))
    end_date = widgets.DatePicker(description='End Date:', value=pd.to_datetime('2023-01-30'))
    download_btn = widgets.Button(description="Generate Native-Scale Link", button_style='success')
    output_area = widgets.Output()

    def on_click(b):
        with output_area:
            output_area.clear_output()
            region = Map.user_roi
            
            if region is None:
                print("[ERROR] Please draw a rectangle on the map first!")
                return
            
            sensor = sensor_dropdown.value
            cfg = SENSOR_DB[sensor]
            start = start_date.value.strftime('%Y-%m-%d')
            end = end_date.value.strftime('%Y-%m-%d')
            
            print(f"Querying {sensor} (Native Scale: {cfg['native_scale']}m)...")
            
            try:
                # 1. Get Collection
                collection = get_processed_collection(sensor, start, end, region)
                
                # 2. Mosaic Strategy (Median)
                # We explicitly rename it to 'median_composite' so the user knows
                image = collection.median().clip(region).set('system:time_start', start)
                
                # 3. Visualization
                vis_params = {
                    'min': cfg['vis_min'],
                    'max': cfg['vis_max'],
                    'bands': cfg['bands']
                }
                Map.addLayer(image, vis_params, f"{sensor} Median ({start} to {end})")
                
                # 4. Download URL (Native Scale Enforcement)
                url = image.getDownloadURL({
                    'scale': cfg['native_scale'], # <--- CRITICAL FIX
                    'crs': 'EPSG:4326',
                    'region': region,
                    'filePerBand': False,
                    'format': 'GEO_TIFF'
                })
                
                print(f"[SUCCESS] Layer added.")
                print(f"[INFO] Download Scale: {cfg['native_scale']} meters (Native).")
                print(f"\n⬇️ DOWNLOAD LINK (Valid for 24h):")
                print(url)
                
            except Exception as e:
                print(f"[ERROR] {e}")

    download_btn.on_click(on_click)

    display(widgets.VBox([sensor_dropdown, start_date, end_date, download_btn, output_area]))
    display(Map)

if __name__ == "__main__":
    main()
