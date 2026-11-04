"""Notebook entry point retained for existing users; no import-time authentication.

    import ee
    ee.Authenticate()  # first use only
    from gee_downloader_safe import main
    main(project='your-project-id')

Install requirements-notebook.txt for this optional interface.
"""
from datetime import date
from researchgee.catalog import CATALOG
from researchgee.config import Analysis


def main(project=None):
    import os
    import geemap
    import ipywidgets as widgets
    from IPython.display import display
    from researchgee import engine
    engine.initialize(project or os.getenv('EE_PROJECT',''))
    view = geemap.Map(center=[23.81,90.41],zoom=9)
    dataset = widgets.Dropdown(options=list(CATALOG),description='Dataset:')
    start = widgets.DatePicker(description='Start:',value=date(2024,1,1))
    end = widgets.DatePicker(description='End excl.:',value=date(2024,2,1))
    button = widgets.Button(description='Preview median',button_style='success')
    output = widgets.Output()
    def preview(_):
        with output:
            output.clear_output()
            try:
                if view.user_roi is None:
                    raise ValueError('Draw a polygon or rectangle first.')
                geometry = view.user_roi.getInfo()
                if geometry.get('type') == 'Feature':
                    geometry = geometry['geometry']
                cfg = CATALOG[dataset.value]
                spec = Analysis(dataset.value,start.value.isoformat(),end.value.isoformat(),geometry,scale=cfg.scale)
                image,meta = engine.build(spec)
                rgb = ['red','green','blue'] if 'red' in cfg.bands else [cfg.bands[0]]
                view.addLayer(image,{'bands':rgb,'min':cfg.minimum,'max':cfg.maximum},dataset.value)
                print(meta)
                print('For time series, export tasks and manifests, run: streamlit run app.py')
            except Exception as exc:
                print(f'Error: {exc}')
    button.on_click(preview)
    display(widgets.VBox([dataset,start,end,button,output]),view)

if __name__ == '__main__':
    main()
