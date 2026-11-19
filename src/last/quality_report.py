"""Aggregate all official dimensions; incomplete inputs never yield a V-score."""
import argparse, hashlib, json
from pathlib import Path
from .quality_score import summarize

CATEGORIES = {
    'Creativity': ['Composition', 'Diversity'],
    'Commonsense': ['Instance_Preservation', 'Motion_Rationality'],
    'Controllability': ['Camera_Motion', 'Complex_Landscape', 'Complex_Plot',
                        'Dynamic_Attribute', 'Dynamic_Spatial_Relationship',
                        'Human_Interaction', 'Motion_Order_Understanding'],
    'Human Fidelity': ['Human_Anatomy', 'Human_Clothes', 'Human_Identity'],
    'Physics': ['Material', 'Mechanics', 'Multi-View_Consistency', 'Thermotics'],
}


def aggregate(dimensions, complete_inputs):
    categories = {}
    missing = []
    for category, names in CATEGORIES.items():
        values = []
        for name in names:
            item = dimensions.get(name, {})
            value = item.get('mean')
            if item.get('status') != 'completed' or value is None:
                missing.append(name)
            else:
                if not 0 <= value <= 1: raise ValueError('Out-of-range dimension mean')
                values.append(value)
        categories[category] = sum(values)/len(values) if len(values) == len(names) else None
    complete = complete_inputs and not missing
    return dict(complete=complete, v_score=sum(categories.values())/5 if complete else None,
                categories=categories, missing_or_invalid_dimensions=missing,
                dimensions=dimensions, scope='Full primary official V-score' if complete else 'Incomplete; no full V-score')


def build(inputs, scores):
    inputs, scores = Path(inputs), Path(scores)
    coverage_bytes = (inputs/'coverage.json').read_bytes()
    coverage = json.loads(coverage_bytes)
    coverage_sha256 = hashlib.sha256(coverage_bytes).hexdigest()
    dimensions = {}; sources = {}
    anchors = {v['path']: v['sha256'] for v in coverage['videos']}
    if len(anchors) != len(coverage['videos']):
        raise ValueError('Duplicate video in quality coverage')
    complete_inputs = coverage['complete']
    assigned_videos = set()
    for name in sum(CATEGORIES.values(), []):
        meta = inputs/(name+'.json'); receipt = scores/name/'receipt.json'
        if not meta.exists() or not receipt.exists(): continue
        rows = json.loads(meta.read_text())
        paths = [path for row in rows for path in row['video_list']]
        if len(set(paths)) != len(paths) or not assigned_videos.isdisjoint(paths):
            raise ValueError('Video assigned more than once in quality dimensions')
        assigned_videos.update(paths)
        count = len(paths)
        required = 60 if name == 'Diversity' else 20
        if count != required: complete_inputs = False
        if name == 'Diversity' and (len(rows) != 3 or any(len(r['video_list']) != 20 for r in rows)):
            complete_inputs = False
        if name != 'Diversity' and (len(rows) != 5 or any(len(r['video_list']) != 4 for r in rows)):
            complete_inputs = False
        state = json.loads(receipt.read_text())
        if 'coverage_sha256' in state and state['coverage_sha256'] != coverage_sha256:
            raise ValueError('Scoring receipt belongs to a different coverage manifest')
        if state.get('dimension') != name: raise ValueError('Dimension identity mismatch')
        if state.get('metadata_sha256') != hashlib.sha256(meta.read_bytes()).hexdigest():
            raise ValueError('Scoring receipt belongs to different input metadata')
        sources[name] = dict(receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest())
        if state['status'] != 'completed':
            dimensions[name] = dict(status=state['status'], mean=None); continue
        if any(path not in anchors for path in paths) or state.get('videos_sha256') != {p: anchors[p] for p in paths}:
            raise ValueError('Scored video hashes differ from the current quality inputs')
        raw = scores/name/'official_result.json'
        checked = summarize(json.loads(raw.read_text()), rows, name)
        if checked['mean'] != state.get('mean'): raise ValueError('Receipt mean differs from official raw scores')
        dimensions[name] = dict(status='completed', **checked)
        sources[name]['raw_sha256'] = hashlib.sha256(raw.read_bytes()).hexdigest()
    result = aggregate(dimensions, complete_inputs and assigned_videos == set(anchors))
    result.update(family=coverage['family'],mode=coverage['mode'],method=coverage['method'],
                  source_hashes=sources, coverage_sha256=coverage_sha256)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','scores','output'): p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args(); result=build(a.inputs,a.scores)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps(dict(complete=result['complete'],v_score=result['v_score'],missing=result['missing_or_invalid_dimensions'])))


if __name__=='__main__': main()
