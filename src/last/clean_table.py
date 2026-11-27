"""Build clean-recovery and V-score tables for one backbone at a time."""
import argparse
import json
from pathlib import Path

from .quality_report import CATEGORIES, aggregate
from .robustness_table import collect, collect_disjoint


METHODS = {
    'reference': ('No-mark', '—', '—'),
    'videomark': ('VideoMark', 'No', 'Non-blind'),
    'videoshield': ('VideoShield', 'No', 'Non-blind'),
    'sigmark': ('SIGMark', 'No', 'Blind'),
    'lfg': ('LFG', 'Yes', 'Blind'),
    'last': ('LAST', 'Yes', 'Blind'),
}


def scored_dimensions(dimensions):
    count = 0
    for names in CATEGORIES.values():
        for name in names:
            entry = dimensions.get(name, {})
            if entry.get('status') != 'completed' or entry.get('full_dimension_inputs') is False:
                continue
            expected = 3 if name == 'Diversity' else 20
            if entry['expected_units'] != expected:
                continue
            valid, excluded = entry['valid_units'], entry['not_applicable_units']
            if type(valid) is not int or type(excluded) is not int or min(valid, excluded) < 0 or valid + excluded != expected:
                raise ValueError(f'Inconsistent scoring-unit counts for {name}')
            if (entry.get('mean') is None) != (valid == 0):
                raise ValueError(f'Mean and applicable unit count disagree for {name}')
            if valid:
                count += 1
    return count


def render(family, reports, quality, *, disjoint_snapshots=False):
    clean = {}
    collector = collect_disjoint if disjoint_snapshots else collect
    for (backbone, mode, method), cells in collector(reports).items() if reports else ():
        if backbone == family:
            row = cells['clean']
            if row['expected'] != 400 or mode not in ('i2v', 't2v') or method not in METHODS or method == 'reference':
                raise ValueError('Unexpected recovery protocol for the clean table')
            clean[mode, method] = row
    scores = {}
    exclusions = []
    dimension_rows = []
    for q in quality:
        if q['family'] != family:
            continue
        key = (q['mode'], q['method'])
        if key in scores or key[0] not in ('i2v', 't2v') or key[1] not in METHODS:
            raise ValueError('Unexpected or duplicate quality report')
        v = aggregate(q['dimensions'], q['complete'])['v_score']
        if v != q['v_score']:
            raise ValueError('V-score differs from dimension means')
        count = scored_dimensions(q['dimensions'])
        total = sum(map(len, CATEGORIES.values()))
        if v is not None and count != total:
            raise ValueError('Incomplete official scoring units')
        scores[key] = f'pending ({count}/{total} dimensions)' if v is None else f'{v:.3f}'
        for name, entry in q['dimensions'].items():
            if scored_dimensions({name: entry}):
                dimension_rows.append((q['mode'].upper(), METHODS[q['method']][0], name,
                                       entry['mean'], entry['valid_units'], entry['expected_units']))
            if entry.get('status') == 'completed' and entry.get('not_applicable_units', 0):
                exclusions.append(f"{q['mode'].upper()} {METHODS[q['method']][0]}, {name}: "
                                  f"{entry['not_applicable_units']}/{entry['expected_units']}")
    lines = [f'# Clean recovery and video quality — {family}', '',
             '| Method | Inversion-free | Extraction | T2V bit accuracy | T2V V-score | I2V bit accuracy | I2V V-score |',
             '|---|---|---|---:|---:|---:|---:|']
    for method, labels in METHODS.items():
        values = list(labels)
        for mode in ('t2v', 'i2v'):
            row = clean.get((mode, method))
            bit = '—' if method == 'reference' else 'pending'
            if row and row['completed']:
                bit = f"{row['observed_bit_accuracy']:.3f} ({row['completed']}/400)"
            elif row:
                bit = 'pending (0/400)'
            values.extend([bit, scores.get((mode, method), 'pending')])
        lines.append('| ' + ' | '.join(values) + ' |')
    lines.extend(['', 'Bit accuracy is pooled over 512 information bits per completed video. '
                  'Counts below 400 indicate interim observations. V-score requires the full quality report.'])
    if clean:
        lines.extend(['', '### Counts behind the clean bit accuracies', '',
                      '| Mode | Method | Correct information bits | Entire messages recovered |',
                      '|---|---|---:|---:|'])
        for (mode, method), row in sorted(clean.items()):
            if row['completed']:
                lines.append(f"| {mode.upper()} | {METHODS[method][0]} | "
                             f"{row['correct_bits']}/{row['total_bits']} | "
                             f"{row['exact_messages']}/{row['completed']} |")
    if dimension_rows:
        lines.extend(['', '### Official dimension means', '',
                      'Diversity uses prompt groups as scoring units. Other dimensions use videos.', '',
                      '| Mode | Method | Dimension | Mean | Valid / planned units |',
                      '|---|---|---|---:|---:|'])
        for mode, method, name, mean, valid, expected in sorted(dimension_rows):
            lines.append(f'| {mode} | {method} | {name} | {mean:.4f} | {valid}/{expected} |')
    if exclusions:
        lines.extend(['', 'Official scoring units marked inapplicable (excluded from dimension means):',
                      '', *['- ' + label for label in sorted(exclusions)]])
    return '\n'.join(lines) + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--family', choices=('hunyuan', 'wan22'), required=True)
    p.add_argument('--reports', nargs='+', type=Path, default=[])
    p.add_argument('--quality', nargs='+', type=Path, default=[])
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--disjoint-snapshots', action='store_true',
                   help='Pool audited clean results from distinct samples of the same manifest')
    a = p.parse_args()
    if not (a.reports or a.quality):
        p.error('Supply measured reports')
    def read(paths):
        return [json.loads(path.read_bytes()) for path in paths]
    table = render(a.family, read(a.reports), read(a.quality), disjoint_snapshots=a.disjoint_snapshots)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x', encoding='utf-8') as stream:
        stream.write(table)


if __name__ == '__main__':
    main()
