import json
from pathlib import Path
import pytest
from last.null_fit import validate_index,fit_files


def test_partial_duplicate_or_test_ids_rejected_before_file_access():
    root=Path(__file__).resolve().parents[1]/'configs'
    devpath=root/'development_manifest.json';primarypath=root/'primary_manifest.json'
    dev=json.loads(devpath.read_text());primary=json.loads(primarypath.read_text())
    index=[dict(video_id=r['id']) for r in dev['samples']]
    validate_index(index,dev,primary)
    for bad in (index[:-1],index[:-1]+[index[0]],index[:-1]+[dict(video_id='paper-000')]):
        with pytest.raises(ValueError,match='all80'):
            fit_files(bad,devpath,primarypath,'nonexistent-development','nonexistent-primary')
