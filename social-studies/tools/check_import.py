#!/usr/bin/env python3
"""Optional integration test using Anki's Python backend, never a user's collection.

Install `anki` into a separate test environment; this is not a build dependency.
An unsupported backend API is a failed/unsupported test, not a successful import.
"""
from __future__ import annotations
import evidence
import importlib.metadata
import csv
from collections import Counter
import json
import hashlib
import sqlite3
import zipfile
from pathlib import Path
import tempfile
import traceback

ROOT=Path(__file__).resolve().parents[1]


def main() -> int:
    report={**evidence.inputs(ROOT),'artifact_sha256':evidence.sha256(ROOT/'anki/social-studies.apkg'),'backend_test':'not_run','desktop_gui_tested':False,'mobile_sync_tested':False}
    evidence.write(ROOT,'ANKI_IMPORT_TEST.json',report)
    try:
        from anki.collection import Collection, ImportAnkiPackageOptions, ImportAnkiPackageRequest
        from anki.lang import set_lang
        set_lang('en_US')
        expected=json.loads((ROOT/'BUILD_REPORT.json').read_text())['statistics']['anki_cards']
        report['anki_python_version']=importlib.metadata.version('anki')
        with tempfile.TemporaryDirectory(prefix='social-studies-anki-test-') as tmp:
            col=Collection(str(Path(tmp)/'test.anki2'))
            try:
                package=str(ROOT/'anki/social-studies.apkg')
                def import_package(path):
                    return col.import_anki_package(ImportAnkiPackageRequest(
                        package_path=path,
                        options=ImportAnkiPackageOptions(with_scheduling=False, with_deck_configs=False)))
                import_package(package)
                first=col.db.scalar('select count(*) from notes')
                card_count=col.db.scalar('select count(*) from cards')
                assert first==card_count==expected,(first,card_count,expected)
                # Compare independently parsed text formats with the actual Anki import.
                imported=Counter((row[0].split('\x1f')[1],row[0].split('\x1f')[2],tuple(sorted(row[1].split()))) for row in col.db.all('SELECT flds,tags FROM notes'))
                for filename,delimiter in [('cards.csv',','),('cards.tsv','\t')]:
                    with (ROOT/'anki'/filename).open(encoding='utf-8',newline='') as stream:
                        rows=list(csv.reader((line for line in stream if not line.startswith('#')),delimiter=delimiter))
                    assert len(rows)==expected and all(len(row)==3 for row in rows)
                    assert Counter((row[0],row[1],tuple(sorted(row[2].split()))) for row in rows)==imported,filename
                report['csv_tsv_match_imported_html_and_tags']=True
                cid=col.db.scalar('select id from cards order by id limit 1')
                c=col.get_card(cid)
                c.type=2;c.queue=2;c.ivl=12;c.due=42;c.reps=8;c.lapses=1;c.factor=2500
                col.update_card(c)
                before=col.db.first('select type,queue,ivl,due,reps,lapses,factor from cards where id=?',cid)
                gids=set(x[0] for x in col.db.all('select guid from notes'))
                import_package(package)
                second=col.db.scalar('select count(*) from notes')
                after=col.db.first('select type,queue,ivl,due,reps,lapses,factor from cards where id=?',cid)
                assert second==first
                assert gids==set(x[0] for x in col.db.all('select guid from notes'))
                assert before==after,(before,after)
                note=col.get_note(c.nid)
                assert note.fields[0] not in col.get_card(cid).question()
                # Exercise a real content update without touching any learner collection.
                patched_db=Path(tmp)/'patched.anki2'
                patched_package=Path(tmp)/'patched.apkg'
                with zipfile.ZipFile(package) as original:
                    patched_db.write_bytes(original.read('collection.anki2'))
                    with sqlite3.connect(patched_db) as db:
                        row=db.execute('SELECT flds FROM notes WHERE guid=?',(note.guid,)).fetchone()
                        assert row is not None
                        updated_fields=row[0]+'<p>更新検証（試験専用）</p>'
                        db.execute('UPDATE notes SET flds=?, mod=mod+100 WHERE guid=?',(updated_fields,note.guid))
                        db.commit()
                    with zipfile.ZipFile(patched_package,'w',zipfile.ZIP_DEFLATED) as output:
                        for name in original.namelist():
                            output.writestr(name,patched_db.read_bytes() if name=='collection.anki2' else original.read(name))
                import_package(str(patched_package))
                assert col.get_note(c.nid).fields[-1].endswith('更新検証（試験専用）</p>')
                assert col.db.scalar('SELECT count(*) FROM notes')==expected
                assert col.db.first('select type,queue,ivl,due,reps,lapses,factor from cards where id=?',cid)==before
                report.update(artifact_sha256=hashlib.sha256(Path(package).read_bytes()).hexdigest(),content_update_tested=True,keyword_only_front=True)
                report.update(backend_test='passed',notes_after_first=first,notes_after_second=second,cards=card_count,stable_guids=True,review_schedule_preserved=True,scope='First import, unchanged re-import, and newer-note content update using isolated temporary collections; existing review state preserved. No desktop GUI, mobile app or sync test.')
            finally:
                col.close()
    except Exception as exc:
        report.update(backend_test='failed_or_unsupported',error_type=type(exc).__name__,error=str(exc))
        traceback.print_exc()
    (ROOT/'ANKI_IMPORT_TEST.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['backend_test']=='passed' else 1


if __name__=='__main__':
    raise SystemExit(main())
