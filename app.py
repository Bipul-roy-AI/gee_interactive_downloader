"""Run with: streamlit run app.py. Local, single-user research application."""
from dataclasses import replace
from datetime import date, datetime, timezone
import json
import os
import pandas as pd
import streamlit as st
from researchgee.catalog import CATALOG, INDICES, OPTICAL, STATIC
from researchgee.config import Analysis, bbox, from_manifest, validate_geometry

st.set_page_config(page_title='Earth Engine | Research Workbench',page_icon='🌍',layout='wide')
st.markdown('''<style>
.stApp {background:#f5f7f5} h1,h2,h3 {color:#183e34}
[data-testid="stSidebar"] {background:#e8efea}
[data-testid="stMetric"] {background:white;border:1px solid #dce5df;border-radius:10px;padding:16px}
.block-container {padding-top:4.5rem} .eyebrow {color:#28765d;letter-spacing:3px;font-size:12px;font-weight:700}
</style>''',unsafe_allow_html=True)
st.markdown('<div class="eyebrow">GEE INTERACTIVE DOWNLOADER · RESEARCH EDITION</div>',unsafe_allow_html=True)
st.title('From satellite scenes to reproducible research')
st.caption('Explore evidence. Inspect quality. Export data with its methods.')

with st.sidebar:
    st.header('Research workspace')
    project = st.text_input('Google Cloud project ID',value=os.getenv('EE_PROJECT',''),placeholder='your-earth-engine-project')
    if st.button('Connect to Earth Engine',type='primary'):
        try:
            from researchgee import engine
            engine.initialize(project)
            st.session_state.connected_project = project.strip()
            for key in ('result','inventory','series','stats','change','url'):
                st.session_state.pop(key,None)
            st.success('Connected')
        except Exception as exc:
            st.error(f'Connection failed: {exc}')
    connected = bool(project.strip()) and st.session_state.get('connected_project') == project.strip()
    st.caption('Live session' if connected else 'Setup mode · no live Earth Engine data')
    with st.expander('First-time access'):
        st.write('Register an Earth Engine enabled Cloud project, then authenticate from your local terminal:')
        st.code('earthengine authenticate',language='bash')
        st.write('Enter that project ID above. Credentials remain in your local Google credential store.')
    st.divider()
    st.markdown('**A reproducible workflow**\n\n1. Define your study area\n2. Choose data and methods\n3. Inspect observations\n4. Analyze and export')
    st.caption('Local, single-user app. Do not expose a credentialed session on a public server.')

configure, explore, analyze, exports, methods = st.tabs(['01 · Study design','02 · Map & scenes','03 · Analysis','04 · Export & provenance','05 · Methods & catalog'])

with configure:
    left,right = st.columns([1.1,1])
    with left:
        st.subheader('Choose your evidence')
        dataset = st.selectbox('Dataset',list(CATALOG))
        cfg = CATALOG[dataset]
        st.caption(cfg.note)
        a,b = st.columns(2)
        start = a.date_input('Start date',date(2024,1,1))
        end = b.date_input('End date (exclusive)',date(2024,2,1))
        options = ['median','mean','min','max','scene'] + (['sum'] if cfg.kind == 'rain' else [])
        reducer = st.selectbox('Temporal operation',options,disabled=cfg.kind in STATIC)
        scene_id = st.text_input('Exact scene ID (for scene operation)',help='Copy a scene_id from Map & scenes.') if reducer == 'scene' else ''
        index = st.selectbox('Spectral index',['None',*INDICES,'EVI'],disabled=cfg.kind not in OPTICAL)
        if cfg.kind not in OPTICAL:
            index = 'None'
        cloud = st.slider('Maximum scene cloud cover (%)',0,100,80,disabled=cfg.kind not in ('s2','landsat'))
        orbit = st.selectbox('Radar orbit direction',['DESCENDING','ASCENDING'],disabled=cfg.kind != 's1')
        relative = st.number_input('Relative radar orbit (0 = all)',0,175,0,disabled=cfg.kind != 's1')
    with right:
        st.subheader('Define your study area')
        st.caption('WGS84 longitude/latitude bounds, or a Polygon/MultiPolygon GeoJSON. Uploaded AOIs replace bounds.')
        a,b = st.columns(2)
        west = a.number_input('West',-180.,180.,90.30,format='%.5f')
        east = b.number_input('East',-180.,180.,90.50,format='%.5f')
        south = a.number_input('South',-90.,90.,23.70,format='%.5f')
        north = b.number_input('North',-90.,90.,23.90,format='%.5f')
        upload = st.file_uploader('Upload AOI GeoJSON',type=['geojson','json'])
        scale = st.number_input('Analysis / export scale (metres)',1.,100000.,float(cfg.scale),key='scale_'+dataset)
        crs = st.text_input('Analysis / export CRS','EPSG:4326')
        st.caption('Scale specifies the output grid. Smaller pixels do not create finer source information. Use a suitable projected CRS for your region.')
        imported = st.file_uploader('Or replay an exported manifest',type=['json'],key='manifest')
        st.caption('When provided, manifest parameters override all controls above. Remove the file to edit controls again.')
    try:
        geometry = validate_geometry(json.load(upload)) if upload else bbox(west,south,east,north)
        # Scene inventory can be requested before a scene is chosen.
        spec = Analysis(dataset,str(start),str(end),geometry,reducer,scale,crs,index,cloud,orbit,relative,scene_id)
        if imported:
            spec = from_manifest(json.load(imported))
            st.info(f'Manifest active: {spec.dataset}, {spec.start} to {spec.end}, {spec.reducer}, {spec.scale} m.')
        if CATALOG[spec.dataset].kind in STATIC:
            spec = replace(spec,reducer='median',scene_id='')
        query_spec = replace(spec,reducer='median',scene_id='')
        query_spec.validate()
        cfg = CATALOG[spec.dataset]
    except (ValueError,TypeError,KeyError) as exc:
        st.error(f'Invalid study design: {exc}')
        st.stop()
    st.info('Dates use [start, end). Indices are computed per scene before temporal reduction. Composites summarize a period and can conceal short-lived events.')

# Bind every result to immutable configuration. Changing controls cannot export a stale result.
try:
    fingerprint = spec.fingerprint()
except ValueError:
    fingerprint = None
result = st.session_state.get('result')
active = result is not None and result['fingerprint'] == fingerprint and result['project'] == project.strip()
if result and not active:
    st.warning('Study design changed. Build a new result before analysis or export.')

def run_live(action):
    try:
        from researchgee import engine
        # EE keeps project state globally: reset for each explicitly triggered operation.
        engine.initialize(project)
        with st.spinner('Earth Engine is processing your request…'):
            return action(engine)
    except Exception as exc:
        st.error(str(exc))
        return None

with explore:
    a,b,c = st.columns(3)
    a.metric('Data source',spec.dataset)
    b.metric('Output grid',f'{spec.scale:g} m')
    c.metric('Result',str(result['metadata']['scene_count'] or 'Static')+' scenes' if active else 'Not built')
    st.subheader('Inspect before you analyze')
    c1,c2 = st.columns(2)
    if c1.button('List matching scenes',disabled=not connected or cfg.kind in STATIC):
        value = run_live(lambda engine: engine.inventory(query_spec))
        if value is not None:
            st.session_state.inventory = (query_spec.fingerprint(),value)
    if c2.button('Build map result',type='primary',disabled=not connected):
        value = run_live(lambda engine: engine.build(spec))
        if value is not None:
            img,metadata = value
            st.session_state.result = {'image':img,'metadata':metadata,'fingerprint':spec.fingerprint(),'project':project.strip(),'created':datetime.now(timezone.utc).isoformat()}
            for key in ('series','stats','change','url'):
                st.session_state.pop(key,None)
            st.rerun()
    inv = st.session_state.get('inventory')
    if inv and inv[0] == query_spec.fingerprint():
        total,rows = inv[1]
        st.caption(f'{total} matching scenes; showing the first {len(rows)} in acquisition order. Cloud cover filtering is scene-wide, not AOI-specific.')
        st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
    bands = list(cfg.bands) + ([spec.index] if spec.index != 'None' else [])
    view_band = st.selectbox('Map / analysis band',bands,index=len(bands)-1 if spec.index != 'None' else 0)
    a,b = st.columns(2)
    vmin = a.number_input('Map minimum',value=float(-1 if view_band in (*INDICES,'EVI') else cfg.minimum))
    vmax = b.number_input('Map maximum',value=float(1 if view_band in (*INDICES,'EVI') else cfg.maximum))
    rgb = st.checkbox('Show natural-color RGB',value=cfg.kind in OPTICAL,disabled=cfg.kind not in OPTICAL)
    st.caption('Adjust display bounds for the selected band (e.g. temperature 260–320 K). Display settings do not change exported values.')
    import folium
    from streamlit_folium import st_folium
    m = folium.Map(tiles=None)
    folium.TileLayer('OpenStreetMap').add_to(m)
    layer = folium.GeoJson(spec.geometry,name='Study area',style_function=lambda _: {'color':'#20a679','weight':3,'fillOpacity':0.06}).add_to(m)
    m.fit_bounds(layer.get_bounds())
    if active and connected:
        if st.button('Load / refresh image tiles'):
            if vmin >= vmax:
                st.error('Map minimum must be smaller than maximum.')
            else:
                vis = {'bands':['red','green','blue'] if rgb and cfg.kind in OPTICAL else [view_band],'min':vmin,'max':vmax}
                tiles = run_live(lambda engine: result['image'].getMapId(vis)['tile_fetcher'].url_format)
                if tiles:
                    st.session_state.tiles = (fingerprint,tiles)
        tile_state = st.session_state.get('tiles')
        if tile_state and tile_state[0] == fingerprint:
            folium.TileLayer(tiles=tile_state[1],attr='Google Earth Engine · '+cfg.asset,name='Analysis result',overlay=True).add_to(m)
    folium.LayerControl().add_to(m)
    st_folium(m,height=440,width=None,returned_objects=[],key='research_map')
    if not active:
        st.caption('AOI preview only. No satellite result has been retrieved. Connect and build a result to load Earth Engine tiles.')

with analyze:
    st.subheader('Measure patterns, retain uncertainty')
    st.caption(f'Current band: {view_band}. Regional means are pixel summaries on the chosen analysis grid, not area-weighted estimates.')
    a,b = st.columns(2)
    if a.button('Calculate regional statistics',disabled=not(active and connected)):
        value = run_live(lambda engine: engine.statistics(result['image'],spec,view_band))
        if value is not None:
            st.session_state.stats = (fingerprint,view_band,value)
    if b.button('Calculate per-scene time series',disabled=not(active and connected) or cfg.kind in STATIC):
        value = run_live(lambda engine: engine.time_series(query_spec,view_band))
        if value is not None:
            st.session_state.series = (fingerprint,view_band,value)
    stats = st.session_state.get('stats')
    if active and stats and stats[:2] == (fingerprint,view_band):
        st.json(stats[2])
        st.caption('Count is the number of valid output pixels, not the number of independent observations. Null statistics indicate no valid pixels.')
    series = st.session_state.get('series')
    if active and series and series[:2] == (fingerprint,view_band):
        frame = pd.DataFrame(series[2])
        if not frame.empty:
            st.dataframe(frame,hide_index=True,width='stretch')
            if view_band+'_mean' in frame:
                st.line_chart(frame,x='date',y=view_band+'_mean')
            st.download_button('Download time-series CSV',frame.to_csv(index=False),'time_series.csv','text/csv')
        else:
            st.info('No observations.')
    st.divider()
    st.subheader('Compare two periods')
    st.caption('Difference = current − baseline, using the same dataset, AOI, filters, reducer, band and grid. Negative dNBR here means current NBR decreased; conventional burn-severity dNBR often uses the opposite sign. No automatic hazard classification.')
    a,b = st.columns(2)
    baseline_start = a.date_input('Baseline start',date(2023,1,1))
    baseline_end = b.date_input('Baseline end (exclusive)',date(2023,2,1))
    if st.button('Calculate change statistics',disabled=not(active and connected) or cfg.kind in STATIC or spec.reducer == 'scene'):
        def change(engine):
            baseline_spec = replace(spec,start=str(baseline_start),end=str(baseline_end))
            baseline,meta = engine.build(baseline_spec)
            delta = engine.difference(result['image'].select(view_band),baseline.select(view_band),spec,baseline_spec)
            return {'statistics':engine.statistics(delta,spec,view_band),'baseline':baseline_spec.manifest(),'baseline_sources':meta,'band':view_band,'sign':'current minus baseline'}
        value = run_live(change)
        if value is not None:
            st.session_state.change = (fingerprint,view_band,value)
    changed = st.session_state.get('change')
    if active and changed and changed[:2] == (fingerprint,view_band):
        st.json(changed[2])
        st.download_button('Download change report',json.dumps(changed[2],indent=2),'change_report.json','application/json')

with exports:
    st.subheader('Take the data and the methods with you')
    st.write('GeoTIFF for GIS • CSV for time series • JSON for reproducible methods')
    if fingerprint:
        manifest = spec.manifest()
        if active:
            manifest.update(result['metadata'])
            manifest['generated_at_utc'] = result['created']
        st.download_button('Download analysis manifest',json.dumps(manifest,indent=2),'analysis_manifest.json','application/json')
    else:
        st.info('Choose a valid scene ID to save this configuration.')
    available_bands = bands + ([x+'_count' for x in bands] if cfg.kind not in STATIC else [])
    output_bands = st.multiselect('Export bands (include *_count for observation support)',available_bands,default=bands)
    if fingerprint:
        export_manifest = dict(manifest, export_bands=output_bands, export_dtype='float32', resampling='nearest', task_ids=st.session_state.get('submitted',[]))
        st.download_button('Download export manifest',json.dumps(export_manifest,indent=2),'export_manifest.json','application/json')
    st.caption('Exported values are numeric science bands, not rendered RGB colors. All bands use float32 in the requested output grid. Default resampling is nearest neighbor.')
    if st.button('Create small GeoTIFF download link',disabled=not(active and connected and output_bands)):
        value = run_live(lambda engine: engine.download_url(result['image'],spec,output_bands))
        if value:
            st.session_state.url = (fingerprint,tuple(output_bands),value)
    url = st.session_state.get('url')
    if active and url and url[:2] == (fingerprint,tuple(output_bands)):
        st.link_button('Download GeoTIFF',url[2])
    st.caption('Direct requests are limited by Earth Engine to 32 MB and 10,000 pixels per dimension. Links are temporary; regenerate if expired. For larger areas, use Drive.')
    a,b = st.columns(2)
    name = a.text_input('Export name','gee_research_result')
    folder = b.text_input('Google Drive folder','GEE_Research')
    if st.button('Start Google Drive export',disabled=not(active and connected and output_bands)):
        task_id = run_live(lambda engine: engine.export_drive(result['image'],spec,output_bands,name,folder))
        if task_id:
            st.session_state.setdefault('submitted',[]).append({'id':task_id,'fingerprint':fingerprint,'bands':output_bands,'name':name,'folder':folder})
            st.success(f'Export submitted, not yet completed: {task_id}')
    if st.button('Refresh task status',disabled=not connected):
        value = run_live(lambda engine: [t.status() for t in engine.ee.batch.Task.list()[:50]])
        if value is not None:
            st.dataframe(pd.DataFrame(value),width='stretch')
    st.caption('Task panel shows up to 50 recent tasks for your account. Manage cancellation in the Earth Engine task manager.')
    st.link_button('Open Earth Engine task manager','https://code.earthengine.google.com/tasks')

with methods:
    st.subheader('Know what each product means')
    st.dataframe(pd.DataFrame([{'Dataset':name,'Asset':item.asset,'Default grid (m)':item.scale,'Units':item.units} for name,item in CATALOG.items()]),hide_index=True,width='stretch')
    st.markdown('''
- **Cloud quality:** Sentinel-2 SCL and Landsat QA masks precede scaling and index calculation. Masks are imperfect; visually inspect residual cloud, haze and shadow.
- **Temporal support:** use an individual scene for event studies. Scene counts are not independent acquisition-day counts; overlapping granules may occur.
- **Resolution:** multispectral and ancillary QA bands have different native resolutions. Output scale does not improve source resolution.
- **Comparability:** no cross-sensor harmonization, atmospheric correction beyond source products, or universal flood classifier is applied.
- **Reproducibility:** keep the manifest, source IDs, observation counts, exported data, software version and source citation together. Catalog backfills can change a replayed date query.
- **Coverage:** per-scene time series retain missing values and reject more than 250 scenes. Regional reductions fail explicitly if too large; no automatic scale coarsening.
''')
    st.markdown('[Earth Engine data catalog](https://developers.google.com/earth-engine/datasets) · [Access and authentication](https://developers.google.com/earth-engine/guides/auth)')
