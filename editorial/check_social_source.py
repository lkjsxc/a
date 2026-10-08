"""Read-only audit of authored social-studies text; never builds or publishes.

Run from this repository with Python 3: python editorial/check_social_source.py
The report is printed to stdout. This is not an Anki, browser, or deployment test.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'editorial/social-baseline-20261008.json'


def parse_source(path: Path, extension: bool) -> list[dict]:
    lessons = []
    current = None
    mode = ''
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        where = f'{path.relative_to(ROOT)}:{number}'
        prefix = '@extend ' if extension else '@lesson '
        if line.startswith(prefix):
            if current is not None:
                raise ValueError(f'{where}: unclosed lesson')
            fields = line[len(prefix):].split('|')
            if len(fields) != (1 if extension else 6):
                raise ValueError(f'{where}: malformed header')
            current = dict(id=fields[0], text=[], cards=[], questions=[])
            if not extension:
                current.update(title=fields[1], subject=fields[2], year=fields[3],
                               prerequisites=[] if fields[4] == '-' else fields[4].split(','),
                               references=fields[5].split(','))
            mode = ''
        elif line in ('@text', '@cards', '@questions'):
            if current is None:
                raise ValueError(f'{where}: section outside lesson')
            mode = line[1:]
        elif line == '@end':
            if current is None:
                raise ValueError(f'{where}: unexpected end')
            lessons.append(current)
            current = None
            mode = ''
        elif line.startswith('@'):
            raise ValueError(f'{where}: unknown directive')
        elif line.strip():
            if current is None or not mode:
                raise ValueError(f'{where}: content without section')
            value = line if mode == 'text' else line.split('|')
            expected = 7 if mode == 'cards' else 6
            if mode != 'text' and (len(value) != expected or not all(value)):
                raise ValueError(f'{where}: invalid fields')
            current[mode].append(value)
    if current is not None:
        raise ValueError(f'{path}: unclosed lesson')
    return lessons


def audit() -> dict:
    baseline = json.loads(BASELINE.read_text(encoding='utf-8'))
    sources = sorted((ROOT / 'social-studies/source').glob('*.txt'))
    extensions = sorted((ROOT / 'social-studies/source/expansion').glob('*.txt'))
    lessons = {}
    for path in sources:
        for lesson in parse_source(path, False):
            if lesson['id'] in lessons:
                raise ValueError('Duplicate lesson ' + lesson['id'])
            lessons[lesson['id']] = lesson
    extended = set()
    for path in extensions:
        for extra in parse_source(path, True):
            lid = extra['id']
            if lid not in lessons or lid in extended:
                raise ValueError('Unknown or repeated extension ' + lid)
            extended.add(lid)
            for key in ('text', 'cards', 'questions'):
                lessons[lid][key].extend(extra[key])
    expected_ids = [old['id'] for old in baseline['lessons']]
    assert list(lessons) == expected_ids, 'Lesson order or identity changed'
    assert len(lessons) == 76 and len(extended) == 72
    refs = json.loads((ROOT / 'social-studies/source/sources.json').read_text())['sources']
    visiting, completed = set(), set()

    def check_prerequisites(lid: str) -> None:
        assert lid not in visiting, 'Cyclic prerequisite ' + lid
        if lid in completed:
            return
        visiting.add(lid)
        for previous in lessons[lid]['prerequisites']:
            assert previous in lessons, 'Unknown prerequisite ' + previous
            check_prerequisites(previous)
        visiting.remove(lid)
        completed.add(lid)

    rows, fronts, questions = [], [], {}
    for old in baseline['lessons']:
        lid = old['id']
        now = lessons[lid]
        check_prerequisites(lid)
        assert all(key in refs for key in now['references']), lid
        identities = {lid + '-' + c[0]: c[2] for c in now['cards']}
        assert len(identities) == len(now['cards']), 'Repeated card ID ' + lid
        assert all(identities[key] == front for key, front in
                   zip(old['original_ids'], old['original_fronts'])), lid
        assert len(now['questions']) == 6, lid
        assert {q[0] for q in now['questions']} == {'01', '02', '03', '04', '05', '06'}, lid
        assert all(c[1] in ('S', 'A') for c in now['cards']), lid
        assert all(q[1] in ('S', 'A') for q in now['questions']), lid
        fronts.extend(unicodedata.normalize('NFKC', c[2]).strip() for c in now['cards'])
        questions.update({lid + '-Q' + q[0]: q for q in now['questions']})
        size = len(''.join(''.join(now['text']).split()))
        rows.append(dict(id=lid, title=now['title'], before_body_characters=old['body_characters'],
                         after_body_characters=size, cards=len(now['cards']), questions=6))
    duplicates = [word for word, count in Counter(fronts).items() if count > 1]
    assert not duplicates, duplicates
    foundation = (ROOT / 'social-studies/source/00-foundation.txt').read_text()
    assert not re.search(r'最初の一歩|してみましょう|答えよう|書こう|説明しよう|社会を学ぶ入口', foundation)
    assert '正の相関' in foundation and '負の相関' in foundation

    checked = []
    # Bind each numerical check to the actual authored question and answer text.
    def example(qid: str, inputs: tuple[str, ...], outputs: tuple[str, ...], valid: bool) -> None:
        q = questions[qid]
        assert all(text in q[3] for text in inputs), qid + ' input changed'
        assert all(text in q[4] for text in outputs), qid + ' answer changed'
        assert valid, qid + ' arithmetic'
        checked.append(qid)

    example('F02-Q01', ('24万人', '800'), ('300人',), 240000 / 800 == 300)
    example('F02-Q02', ('80トン', '100トン'), ('25％',), (100 - 80) / 80 * 100 == 25)
    example('F02-Q04', ('200トン', '115'), ('230トン', '15％'), 200 * Fraction(115, 100) == 230)
    example('F02-Q05', ('10人', '20分', '20人', '35分'), ('30分',), (10 * 20 + 20 * 35) / 30 == 30)
    example('F03-Q01', ('50,000', '3センチメートル'), ('1.5キロメートル',), 3 * 50000 / 100000 == 1.5)
    example('F03-Q04', ('50,000', '2倍', '2センチメートル'), ('4センチメートル', '1キロメートル'), 4 * 25000 / 100000 == 1)
    example('F04-Q04', ('紀元前3年', '西暦3年'), ('5年',), 3 + 3 - 1 == 5)
    example('G02-Q04', ('7月2日18時', '8時間', '7時間', '9時間'), ('7月2日10時',), datetime(2000, 7, 2, 18) + timedelta(hours=8 - 16) == datetime(2000, 7, 2, 10))
    example('G03-Q04', ('31℃', '19℃'), ('12℃',), 31 - 19 == 12)
    example('G07-Q04', ('200', '単価5', '250', '単価3'), ('1,000', '750'), 200 * 5 == 1000 and 250 * 3 == 750)
    example('G10-Q04', ('2人', '100ha', '400t', '4人', '20ha', '120t'), ('200t', '30t', '4t', '6t'), (400 / 2, 120 / 4, 400 / 100, 120 / 20) == (200, 30, 4, 6))
    example('G11-Q05', ('1,000ha', '2t/ha', '900ha', '3t/ha'), ('2,000t', '2,700t'), 1000 * 2 == 2000 and 900 * 3 == 2700)
    example('G17-Q04', ('500ha', '4t/ha', '450ha', '5t/ha'), ('2,000t', '2,250t', '250t'), 450 * 5 - 500 * 4 == 250)
    example('G18-Q04', ('50kW', '4時間', '100kW', '1時間'), ('200kWh', '100kWh'), 50 * 4 == 200 and 100 * 1 == 100)
    example('G19-Q04', ('8トン', '200km', '20トン', '50km'), ('1,600', '1,000'), 8 * 200 == 1600 and 20 * 50 == 1000)
    example('G24-Q04', ('10万人', '3万人', '5万人'), ('8万人', '80％'), 10 + 3 - 5 == 8 and Fraction(8, 10) * 100 == 80)
    example('G27-Q05', ('200世帯', '120世帯'), ('60％',), 120 / 200 * 100 == 60)
    example('H12-Q04', ('面積4', '評価2石', '面積2', '評価5石'), ('8石', '10石'), 4 * 2 == 8 and 2 * 5 == 10)
    example('H15-Q04', ('100', '20', '30'), ('80', '70', '10'), 100 - 20 == 80 and 100 - 30 == 70)
    example('H20-Q04', ('6円', '2円', '1円'), ('3単位', '6単位'), 6 / 2 == 3 and 6 / 1 == 6)
    example('H27-Q05', ('100', '80', '50'), ('30',), 80 - 50 == 30)
    example('C02-Q04', ('100万円', '20万円', '150万円', '10万円', '5年'), ('200万円',), 100 + 20 * 5 == 150 + 10 * 5 == 200)
    example('C03-Q04', ('300人', '210人', '150人', '95人'), ('200人', '100人', 'できません'), 210 >= 300 * Fraction(2, 3) and 95 < 150 * Fraction(2, 3))
    example('C03-Q05', ('510票', '490票'), ('51％',), Fraction(510, 510 + 490) * 100 == 51)
    example('C05-Q04', ('三つ', '51票', '49票'), ('51％', '100％'), Fraction(51 * 3, (51 + 49) * 3) * 100 == 51)
    example('C05-Q05', ('1,000人', '600人', '360票'), ('60％', '36％'), Fraction(360, 600) * 100 == 60 and Fraction(360, 1000) * 100 == 36)
    example('C09-Q06', ('2,000万円', '2万人', '1,500万円', '1万人'), ('1,000円', '1,500円'), 20000000 / 20000 == 1000 and 15000000 / 10000 == 1500)
    example('C10-Q04', ('1,000円', '3,000円', '6回'), ('16,000円', '2,667円'), 1000 + 3000 * 5 == 16000 and round(16000 / 6) == 2667)
    example('C11-Q05', ('80', '200'), ('80', '120', '200'), 200 - 80 == 120 and 80 + 120 == 200)
    example('C12-Q04', ('2,000円', '500円', '300円', '10個'), ('5,000円', '0円'), 500 * 10 == 2000 + 300 * 10 == 5000)
    example('C13-Q04', ('100', '10％', '2年間'), ('120', '121'), 100 + 100 * Fraction(1, 10) * 2 == 120 and 100 * Fraction(11, 10) ** 2 == 121)
    example('C13-Q05', ('100', '120', '126'), ('26％', '5％'), Fraction(126 - 120, 120) * 100 == 5 and 126 - 100 == 26)
    example('C14-Q04', ('10％', '100万円', '20万円', '1万円'), ('7万円',), (100 - 20) * Fraction(1, 10) - 1 == 7)
    example('C14-Q05', ('収入80', '支出90', '国債費20'), ('10の赤字', '30'), 80 - 90 == -10 and 90 + 20 - 80 == 30)
    example('C15-Q04', ('10,000円', '20％'), ('2,000円', '8,000円'), 10000 * Fraction(20, 100) == 2000 and 10000 - 2000 == 8000)
    example('C16-Q04', ('布10', '穀物20', '布4', '穀物12'), ('Aは2', 'Bは3'), 20 / 10 == 2 and 12 / 4 == 3)
    example('C16-Q05', ('10ドル', '120円', '150円'), ('1,200円', '1,500円', '25％'), Fraction(1500 - 1200, 1200) * 100 == 25)
    example('C18-Q04', ('10から8', '100個から150個'), ('1,000', '1,200', '20％'), 8 * 150 == 1200 and Fraction(1200 - 1000, 1000) * 100 == 20)
    after = sum(row['after_body_characters'] for row in rows)
    assert len(fronts) == 2058 and len(questions) == 456
    return dict(status='passed', scope='authored_source_only', baseline_commit=baseline['commit'],
                measurement='Main @text only, whitespace removed; headings and inline source URLs retained. No vocabulary table, question, answer, HTML/ruby or duplicate format is counted.',
                before_body_characters=baseline['total_body_characters'], after_body_characters=after,
                body_ratio=after / baseline['total_body_characters'], lesson_count=len(lessons),
                original_note_identities_preserved=True, duplicate_normalized_fronts=duplicates,
                before_questions=baseline['total_questions'], after_questions=len(questions),
                lesson_notes=len(fronts), atlas_notes_from_unchanged_baseline=47,
                intended_anki_notes=len(fronts) + 47,
                arithmetic_spot_checks=checked, foundation_rewritten=True,
                reference_ids_and_prerequisite_graph_valid=True,
                artifact_build_tested=False, anki_upgrade_tested=False, browser_tested=False,
                main_updated=False, deployment_tested=False,
                source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in [BASELINE, *sources, *extensions]}, lessons=rows)


if __name__ == '__main__':
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
