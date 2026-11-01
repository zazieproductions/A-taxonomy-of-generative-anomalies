"""Deterministic, dependency-free research figures; no source text is published."""
import argparse
from collections import Counter
from html import escape
import json
from pathlib import Path
import re
from statistics import median

COLORS = ['#38bdf8', '#c4b5fd', '#34d399', '#fbbf24']
BG, FG, MUTED = '#0b1220', '#eef2ff', '#a9b8ce'


def lexical_metrics(completion, prompt=''):
    """Unicode word heuristics, not model tokens or semantic measurements."""
    words = re.findall(r'\b\w+\b', completion.casefold())
    prompt_words = set(re.findall(r'\b\w+\b', prompt.casefold()))
    n = len(words)
    grams = list(zip(words, words[1:], words[2:]))
    return {
        'words': n,
        'ttr': len(set(words)) / n if n else None,
        'repeated_trigrams': 1 - len(set(grams)) / len(grams) if grams else None,
        'prompt_overlap': sum(w in prompt_words for w in words) / n if n else None,
    }


def temperature_band(value):
    if value is None:
        return 'Missing'
    if value < 0.1:
        return '< 0.1'
    if value < 1:
        return '0.1–<1'
    if value == 1:
        return '1.0'
    if value <= 2:
        return '>1–2'
    return '> 2'


class Figure:
    def __init__(self, title, subtitle, height=500):
        self.height = height
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}" role="img" aria-labelledby="title desc">',
                      f'<title id="title">{escape(title)}</title><desc id="desc">{escape(subtitle)}</desc>',
                      f'<rect width="1000" height="{height}" rx="18" fill="{BG}"/>']
        self.text(32, 40, title, size=24)
        self.text(32, 68, subtitle, MUTED, 13)

    def text(self, x, y, text, color=FG, size=14, anchor='start'):
        self.parts.append(f'<text x="{x}" y="{y}" fill="{color}" font-family="system-ui, sans-serif" font-size="{size}" text-anchor="{anchor}">{escape(str(text))}</text>')

    def rect(self, x, y, w, h, color, opacity=1):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="{color}" opacity="{opacity}"/>')

    def circle(self, x, y, color, label):
        self.parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.5" fill="{color}" fill-opacity="0.65"><title>{escape(label)}</title></circle>')

    def save(self, path):
        self.text(32, self.height - 20, 'ACS / GENERATIVE ANOMALIES     •     Observational archive · not a model benchmark', MUTED, 12)
        path.write_text('\n'.join(self.parts + ['</svg>']) + '\n')


def build(corpus, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = corpus['generations']
    models = sorted({r['model_identifier'] for r in rows})
    palette = {m: COLORS[i % len(COLORS)] for i, m in enumerate(models)}
    metrics = {r['generation_id']: lexical_metrics(r['completion'], r['prompt']) for r in rows}
    summary = {'generation_count': len(rows), 'models': {}, 'temperature_coverage': {},
               'definitions': {'unit': 'unique generation ID', 'lexical_subset': 'completed runs with at least 3 Unicode word tokens',
                               'quartiles': 'nearest-rank: sorted value at ceil(p*n)-1'}}
    f = Figure('01 / Model coverage & completion accounting', 'All unique generations • counts, not quality or reliability estimates', 400)
    max_count = max((sum(r['model_identifier'] == m for r in rows) for m in models), default=1)
    for i, m in enumerate(models):
        subset = [r for r in rows if r['model_identifier'] == m]
        counts = Counter(r['status'] for r in subset)
        summary['models'][m] = {'runs': len(subset), 'statuses': dict(sorted(counts.items()))}
        y = 120 + i * 95
        f.text(32, y, m, palette[m], 16)
        x = 32
        for status, color in [('completed', '#34d399'), ('cancelled', '#fbbf24')]:
            count = counts[status]
            width = 690 * count / max_count
            f.rect(x, y + 15, width, 28, color)
            x += width
        f.text(750, y + 35, f"n={len(subset)} · {counts['completed']} done / {counts['cancelled']} cancelled", size=12)
    f.text(32, 325, 'GREEN = completed     AMBER = cancelled (may contain partial text)', MUTED)
    f.save(output / 'model-coverage.svg')

    bands = ['< 0.1', '0.1–<1', '1.0', '>1–2', '> 2', 'Missing']
    f = Figure('02 / Sampling coverage matrix', 'Recorded temperature × model • cell labels are run counts; darker = fewer observations', 390)
    for j, band in enumerate(bands):
        f.text(365 + j * 105, 115, band, MUTED, anchor='middle')
    all_counts = [sum(r['model_identifier'] == m and temperature_band(r['sampling'].get('temperature')) == b for r in rows) for m in models for b in bands]
    peak = max(all_counts, default=1) or 1
    for i, m in enumerate(models):
        f.text(32, 170 + i * 75, m, palette[m], 13)
        counts = {}
        for j, band in enumerate(bands):
            n = sum(r['model_identifier'] == m and temperature_band(r['sampling'].get('temperature')) == band for r in rows)
            counts[band] = n
            f.rect(320 + j * 105, 135 + i * 75, 92, 56, palette[m], 0.08 + 0.8 * n / peak)
            f.text(366 + j * 105, 169 + i * 75, n, anchor='middle')
        summary['temperature_coverage'][m] = counts
    f.text(32, 325, 'Prompts, seeds, penalties and candidate filters co-vary. No isolated temperature effect.', MUTED, 13)
    f.save(output / 'sampling-matrix.svg')

    eligible = [r for r in rows if r['status'] == 'completed' and metrics[r['generation_id']]['words'] >= 3]
    f = Figure('03 / Lexical variety across completion length', f'Completed text only · ≥3 Unicode word tokens · n={len(eligible)} · each point is one generation', 560)
    xmax = max((metrics[r['generation_id']]['words'] for r in eligible), default=1)
    for j in range(6):
        value = j / 5
        y = 420 - value * 290
        f.rect(95, y, 840, 1, '#26354b')
        f.text(78, y + 4, f'{value:.1f}', MUTED, 12, 'end')
        f.text(95 + value * 840, 445, round(value * xmax), MUTED, 12, 'middle')
    f.text(95, 108, 'Type-token ratio (unique forms / words)', MUTED, 13)
    f.text(515, 472, 'Completion length / Unicode word tokens (not model tokens)', MUTED, 13, 'middle')
    for r in eligible:
        met = metrics[r['generation_id']]
        f.circle(95 + met['words'] / xmax * 840, 420 - met['ttr'] * 290, palette[r['model_identifier']], f"{r['model_identifier']} | {met['words']} words | TTR {met['ttr']:.3f}")
    for i, m in enumerate(models):
        f.text(95 + i * 445, 505, m, palette[m], 13)
    f.save(output / 'lexical-landscape.svg')

    f = Figure('04 / Linguistic fingerprints · distributions', 'Completed text ≥3 words • line = min–max; box = Q1–Q3; dot = median • no quality ranking', 590)
    dimensions = [('ttr', 'Lexical variety / TTR'), ('repeated_trigrams', 'Repeated trigram fraction'), ('prompt_overlap', 'Prompt-word overlap')]
    import math
    for d, (key, label) in enumerate(dimensions):
        y = 135 + d * 125
        f.text(32, y - 20, label, size=16)
        for j in range(6):
            f.text(400 + j * 105, y - 20, f'{j/5:.1f}', MUTED, 11, 'middle')
        for i, m in enumerate(models):
            vals = sorted(metrics[r['generation_id']][key] for r in eligible if r['model_identifier'] == m)
            yy = y + i * 35
            f.text(32, yy + 5, f'{m} (n={len(vals)})', palette[m], 12)
            if not vals:
                continue
            q1, q3 = (vals[max(0, math.ceil(p * len(vals)) - 1)] for p in (.25, .75))
            mid = median(vals)
            summary['models'][m].setdefault('linguistic', {})[key] = {'n': len(vals), 'min': vals[0], 'q1': q1, 'median': mid, 'q3': q3, 'max': vals[-1]}
            f.rect(400 + vals[0] * 525, yy - 1, (vals[-1] - vals[0]) * 525, 2, palette[m])
            f.rect(400 + q1 * 525, yy - 9, max(1, (q3 - q1) * 525), 18, palette[m], .4)
            f.circle(400 + mid * 525, yy, palette[m], f'median={mid:.4f}')
    f.text(32, 530, 'Shared 0–1 axes. Overlap ≠ copying; repetition ≠ pathology; TTR is length-sensitive.', MUTED, 13)
    f.save(output / 'linguistic-fingerprints.svg')
    (output / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', default='data/normalized/corpus.json')
    parser.add_argument('--output', default='docs/figures')
    args = parser.parse_args()
    build(json.loads(Path(args.corpus).read_text()), args.output)


if __name__ == '__main__':
    main()
