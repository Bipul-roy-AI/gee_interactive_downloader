from pathlib import Path
from streamlit.testing.v1 import AppTest

def test_setup_renders_without_credentials():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'),default_timeout=30).run()
    assert not app.exception
    assert 'reproducible research' in app.title[0].value
    build = next(x for x in app.button if x.label == 'Build map result')
    assert build.disabled

def test_dataset_switches_and_invalid_bounds():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'),default_timeout=30).run()
    next(x for x in app.selectbox if x.label == 'Dataset').select('CHIRPS daily rain').run()
    assert not app.exception
    assert 'sum' in next(x for x in app.selectbox if x.label == 'Temporal operation').options
    next(x for x in app.number_input if x.label == 'West').set_value(100.).run()
    assert any('Invalid study design' in error.value for error in app.error)
    assert not app.exception

def test_all_dataset_forms_render():
    from researchgee.catalog import CATALOG
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'),default_timeout=30).run()
    for dataset in CATALOG:
        next(x for x in app.selectbox if x.label == 'Dataset').select(dataset).run()
        assert not app.exception, dataset
