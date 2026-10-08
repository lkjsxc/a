"""Regression tests for authored extension integration (no package writes)."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import build
from expansion import apply_extensions, comparison

class ExpansionTests(unittest.TestCase):
    def test_real_sources_and_comparison(self):
        lessons=apply_extensions(build.ROOT, build.parse_sources())
        build.validate(lessons, json.loads((build.ROOT/'source/sources.json').read_text()), json.loads((build.ROOT/'source/assessments.json').read_text()))
        result=comparison(build.ROOT,lessons)
        self.assertTrue(result['baseline_available'])
        self.assertEqual(result['after_questions'],456)
        self.assertEqual(result['after_anki_cards'],2105)
        self.assertEqual(result['after_body_characters'],sum(len(''.join(l['text'].split())) for l in lessons))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'baseline-20261008.json').write_bytes((build.ROOT.parent/'editorial/social-baseline-20261008.json').read_bytes())
            self.assertEqual(comparison(root,lessons), result)

    def test_ruby_preserves_ampersands(self):
        for value in ('Q&A', '[Q&A](https://example.org/?a=1&b=2)', 'A &amp; B', '文字 &#65;'):
            self.assertEqual(build.ruby(value,{'殷':'いん'}),value)

    def test_invalid_extensions(self):
        sample=dict(id='G01',text='original',cards=[dict(id='G01-01')],questions=[dict(id='G01-Q01')],subject='geography',year='1')
        valid='@extend G01\n@text\nExtra\n@cards\n02|S|Term|-|Meaning|Point|Related\n@questions\n04|A|Compare|Question|Answer|Explanation\n@end\n'
        cases=[valid.replace('G01','X99'),valid+valid,valid.replace('02|S','01|S'),valid.replace('04|A','01|A'),valid.replace('|Meaning|','||'),valid.replace('@cards','@cards\n@cards'),valid.replace('@end\n',''),valid.replace('@text\n',''),valid.replace('02|S','xx|S'),valid.replace('04|A','04|X')]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'source/expansion').mkdir(parents=True)
            path=root/'source/expansion/test.txt'
            for content in cases:
                with self.subTest(content=content):
                    path.write_text(content)
                    with self.assertRaises(ValueError):apply_extensions(root,[copy.deepcopy(sample)])
            path.write_text(valid)
            lessons=[copy.deepcopy(sample)]
            apply_extensions(root,lessons)
            self.assertEqual(len(lessons[0]['cards']),2)
            with self.assertRaises(ValueError):apply_extensions(root,lessons)

if __name__=='__main__':unittest.main()
