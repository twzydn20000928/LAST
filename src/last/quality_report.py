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
            if item.get('status') != 'completed' or value is None or item.get('full_dimension_inputs') is False:
                missing.append(name)
            else:
                if not 0 <= value <= 1: raise ValueError('Out-of-range dimension mean')
                values.append(value)
        categories[category] = sum(values)/len(values) if len(values) == len(names) else None
    complete = complete_inputs and not missing
    return dict(complete=complete, v_score=sum(categories.values())/5 if complete else None,
                categories=categories, missing_or_invalid_dimensions=missing,
                dimensions=dimensions, scope='Full primary official V-score' if complete else 'Incomplete; no full V-score')


def build(inputs, scores, previous=()):
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
    selected = {}
    for name, original_inputs, result_dir in previous:
        if name not in sum(CATEGORIES.values(), []) or name in selected:
            raise ValueError('Unknown or duplicate prior dimension')
        if (scores/name/'receipt.json').exists():
            raise ValueError(f'Multiple score sources for {name}')
        selected[name] = (Path(original_inputs), Path(result_dir))
    for name in sum(CATEGORIES.values(), []):
        meta = inputs/(name+'.json'); receipt = scores/name/'receipt.json'
        scoring_coverage_sha = coverage_sha256
        if name in selected:
            original, directory = selected[name]
            original_bytes = (original/'coverage.json').read_bytes()
            old = json.loads(original_bytes)
            if any(not old.get(k) or old[k] != coverage.get(k) for k in ('family','mode','method','manifest_sha256')):
                raise ValueError(f'Prior coverage belongs to another pipeline or manifest: {name}')
            if (original/meta.name).read_bytes() != meta.read_bytes():
                raise ValueError(f'Prior dimension metadata differs: {name}')
            videos = {v['path']:v['sha256'] for v in old['videos']}
            paths = [p for group in json.loads(meta.read_bytes()) for p in group['video_list']]
            if len(videos) != len(old['videos']) or any(p not in videos or videos[p] != anchors.get(p) for p in paths):
                raise ValueError(f'Prior dimension videos differ: {name}')
            receipt = directory/'receipt.json'
            if not receipt.is_file():
                raise ValueError(f'Missing requested prior receipt: {name}')
            scoring_coverage_sha = hashlib.sha256(original_bytes).hexdigest()
        if not meta.exists() or not receipt.exists(): continue
        rows = json.loads(meta.read_text())
        paths = [path for row in rows for path in row['video_list']]
        if len(set(paths)) != len(paths) or not assigned_videos.isdisjoint(paths):
            raise ValueError('Video assigned more than once in quality dimensions')
        assigned_videos.update(paths)
        groups, seeds = (3, 20) if name == 'Diversity' else (5, 4)
        full_dimension_inputs = len(rows) == groups and all(len(r['video_list']) == seeds for r in rows)
        state = json.loads(receipt.read_text())
        if ('coverage_sha256' in state or name in selected) and state.get('coverage_sha256') != scoring_coverage_sha:
            raise ValueError('Scoring receipt belongs to a different coverage manifest')
        if state.get('dimension') != name: raise ValueError('Dimension identity mismatch')
        if state.get('metadata_sha256') != hashlib.sha256(meta.read_bytes()).hexdigest():
            raise ValueError('Scoring receipt belongs to different input metadata')
        sources[name] = dict(receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest())
        if name in selected:
            sources[name]['original_coverage_sha256'] = scoring_coverage_sha
        if state['status'] != 'completed':
            dimensions[name] = dict(status=state['status'], mean=None); continue
        if any(path not in anchors for path in paths) or state.get('videos_sha256') != {p: anchors[p] for p in paths}:
            raise ValueError('Scored video hashes differ from the current quality inputs')
        raw = receipt.parent/'official_result.json'
        checked = summarize(json.loads(raw.read_text()), rows, name)
        if checked['mean'] != state.get('mean'): raise ValueError('Receipt mean differs from official raw scores')
        dimensions[name] = dict(status='completed', full_dimension_inputs=full_dimension_inputs, **checked)
        sources[name]['raw_sha256'] = hashlib.sha256(raw.read_bytes()).hexdigest()
    result = aggregate(dimensions, complete_inputs and assigned_videos == set(anchors))
    result.update(family=coverage['family'],mode=coverage['mode'],method=coverage['method'],
                  source_hashes=sources, coverage_sha256=coverage_sha256)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','scores','output'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--prior-dimension', nargs=3, action='append', default=[],
                   metavar=('DIMENSION','ORIGINAL_INPUTS','RESULT_DIR'))
    a=p.parse_args(); result=build(a.inputs,a.scores,a.prior_dimension)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps(dict(complete=result['complete'],v_score=result['v_score'],missing=result['missing_or_invalid_dimensions'])))


if __name__=='__main__': main()
