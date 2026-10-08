"""Merge individually authored extensions; never manufacture educational content.

Existing lesson/note identifiers remain unchanged. Extension files are UTF-8
text under source/expansion, using @extend, @text, @cards, @questions, @end.
"""
from __future__ import annotations
import copy
import json
import re
from pathlib import Path


def apply_extensions(root: Path, lessons: list[dict]) -> list[dict]:
    merged = copy.deepcopy(lessons)
    by_id = {lesson['id']: lesson for lesson in merged}
    if len(by_id) != len(lessons):
        raise ValueError('Duplicate lesson ID')
    card_ids = {c['id'] for l in merged for c in l['cards']}
    question_ids = {q['id'] for l in merged for q in l['questions']}
    seen: set[str] = set()
    for path in sorted((root / 'source' / 'expansion').glob('*.txt')):
        target = None
        mode = ''
        text: list[str] = []
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            where = f'{path.name}:{number}'
            if line.startswith('@extend '):
                lid = line.removeprefix('@extend ').strip()
                if target is not None or lid not in by_id or lid in seen:
                    raise ValueError(f'{where}: unknown, repeated, or unclosed extension {lid}')
                target = by_id[lid]
                seen.add(lid)
                text = []
                mode = ""
                sections = []
            elif line in ('@text', '@cards', '@questions'):
                if target is None:
                    raise ValueError(f'{where}: section outside extension')
                if line[1:] in sections or len(sections) >= 3 or line[1:] != ('text', 'cards', 'questions')[len(sections)]:
                    raise ValueError(f'{where}: repeated or out-of-order section')
                mode = line[1:]
                sections.append(mode)
            elif line == '@end':
                if target is None:
                    raise ValueError(f'{where}: unexpected end')
                if sections != ['text', 'cards', 'questions'] or not text:
                    raise ValueError(f'{where}: incomplete extension')
                if text:
                    target['text'] += '\n\n' + '\n\n'.join(text)
                target = None
                mode = ''
            elif line.startswith('@'):
                raise ValueError(f'{where}: unknown directive')
            elif line.strip():
                if target is None:
                    raise ValueError(f'{where}: content outside extension')
                fields = line.split('|')
                if mode == 'text':
                    text.append(line)
                elif mode == 'cards' and len(fields) == 7:
                    no, level, front, reading, definition, point, related = fields
                    cid = f'{target["id"]}-{no}'
                    if not all(f.strip() for f in fields) or not re.fullmatch(r'\d{2,3}', no) or level not in ('S', 'A') or cid in card_ids:
                        raise ValueError(f'{where}: invalid or duplicate card {cid}')
                    card_ids.add(cid)
                    target['cards'].append(dict(
                        id=f'{target["id"]}-{no}', level=level, front=front,
                        reading=reading, definition=definition, point=point,
                        related=related, lesson=target['id'],
                        subject=target['subject'], year=target['year']))
                elif mode == 'questions' and len(fields) == 6:
                    no, level, kind, q, a, explanation = fields
                    qid = f'{target["id"]}-Q{no}'
                    if not all(f.strip() for f in fields) or no not in ('04', '05', '06') or level not in ('S', 'A') or qid in question_ids:
                        raise ValueError(f'{where}: invalid or duplicate question {qid}')
                    question_ids.add(qid)
                    target['questions'].append(dict(
                        id=f'{target["id"]}-Q{no}', level=level, kind=kind,
                        q=q, a=a, explanation=explanation))
                else:
                    raise ValueError(f'{where}: malformed {mode} row')
        if target is not None:
            raise ValueError(f'{path}: unclosed extension')
    lessons[:] = merged
    return lessons


def comparison(root: Path, lessons: list[dict]) -> dict:
    canonical = root.parent / 'editorial' / 'social-baseline-20261008.json'
    path = canonical if canonical.exists() else root / 'baseline-20261008.json'
    baseline = json.loads(path.read_text(encoding='utf-8'))
    current = {lesson['id']: lesson for lesson in lessons}
    rows = []
    for old in baseline['lessons']:
        new = current[old['id']]
        new_cards = {card['id']: card for card in new['cards']}
        for note_id, front in zip(old['original_ids'], old['original_fronts']):
            if note_id not in new_cards or new_cards[note_id]['front'] != front:
                raise ValueError(f'Existing note identity changed: {note_id}')
        length = len(''.join(new['text'].split()))
        rows.append(dict(
            lesson=old['id'], before_characters=old['body_characters'],
            after_characters=length, body_ratio=round(length / old['body_characters'], 3),
            before_cards=old['cards'], after_cards=len(new['cards']),
            before_questions=old['questions'], after_questions=len(new['questions'])))
    before = baseline['total_body_characters']
    after = sum(row['after_characters'] for row in rows)
    return dict(
        baseline_available=True,
        baseline_commit=baseline['commit'],
        measurement='Each lesson main-text source only; whitespace removed. Excludes vocabulary tables, answers, generated HTML/ruby, duplicate formats and appendices. Headings and inline source links are retained equally in both versions.',
        before_body_characters=before, after_body_characters=after,
        body_ratio=round(after / before, 3),
        before_anki_cards=baseline['lesson_cards'] + baseline['atlas_cards'],
        after_anki_cards=sum(len(lesson['cards']) for lesson in lessons) + baseline['atlas_cards'],
        before_questions=baseline['total_questions'],
        after_questions=sum(len(lesson['questions']) for lesson in lessons),
        original_note_ids_and_fronts_preserved=True,
        lessons=rows)
