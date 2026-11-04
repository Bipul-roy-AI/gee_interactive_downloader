"""Opt-in read-only live check. Requires local auth; does not submit exports."""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from researchgee import engine
from researchgee.config import Analysis,bbox

engine.initialize(os.environ['EE_PROJECT'])
spec = Analysis('Sentinel-2 SR','2024-01-01','2024-02-01',bbox(90.40,23.80,90.41,23.81),scale=20,index='NDVI')
image,metadata = engine.build(spec)
print(metadata)
print(engine.statistics(image,spec,'NDVI'))
print('Live read-only smoke check completed. Inspect count and values before scientific use.')
