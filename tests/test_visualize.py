import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from anomaly_archive.visualize import build, lexical_metrics, temperature_band


class VisualizeTests(unittest.TestCase):
    def test_word_metrics(self):
        self.assertIsNone(lexical_metrics('')['ttr'])
        self.assertIsNone(lexical_metrics('a b')['repeated_trigrams'])
        m = lexical_metrics('A a a a', 'a')
        self.assertEqual(m['ttr'], .25)
        self.assertEqual(m['repeated_trigrams'], .5)
        self.assertEqual(m['prompt_overlap'], 1)
        self.assertEqual(lexical_metrics('Été été')['ttr'], .5)

    def test_temperature_boundaries(self):
        self.assertEqual([temperature_band(x) for x in [None, 0, .1, 1, 2, 3]],
                         ['Missing', '< 0.1', '0.1–<1', '1.0', '>1–2', '> 2'])

    def test_reproducible_figures_and_accounting(self):
        root = Path(__file__).resolve().parents[1]
        corpus = json.loads((root / 'data/normalized/corpus.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            summary = build(corpus, tmp)
            self.assertEqual(summary['generation_count'], len(corpus['generations']))
            self.assertEqual(sum(m['runs'] for m in summary['models'].values()), len(corpus['generations']))
            for model, counts in summary['temperature_coverage'].items():
                self.assertEqual(sum(counts.values()), summary['models'][model]['runs'])
            for file in Path(tmp).iterdir():
                self.assertEqual(file.read_bytes(), (root / 'docs/figures' / file.name).read_bytes(), file.name)
                if file.suffix == '.svg':
                    ET.parse(file)
                    self.assertNotIn('<script', file.read_text())
