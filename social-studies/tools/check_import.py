#!/usr/bin/env python3
"""Optional integration test using Anki's Python backend, never a user's collection.

Install `anki` into a separate test environment; this is not a build dependency.
An unsupported backend API is a failed/unsupported test, not a successful import.
"""
from __future__ import annotations
import importlib.metadata
import json
from pathlib import Path
import tempfile
import traceback

ROOT=Path(__file__).resolve().parents[1]


def main() -> int:
    report={'backend_test':'not_run','desktop_gui_tested':False,'mobile_sync_tested':False}
    try:
        from anki.collection import Collection
        from anki.importing.apkg import AnkiPackageImporter
        expected=json.loads((ROOT/'BUILD_REPORT.json').read_text())['statistics']['anki_cards']
        report['anki_python_version']=importlib.metadata.version('anki')
        with tempfile.TemporaryDirectory(prefix='social-studies-anki-test-') as tmp:
            col=Collection(str(Path(tmp)/'test.anki2'))
            try:
                package=str(ROOT/'anki/social-studies.apkg')
                importer=AnkiPackageImporter(col,package);importer.run()
                first=col.db.scalar('select count(*) from notes')
                card_count=col.db.scalar('select count(*) from cards')
                assert first==card_count==expected,(first,card_count,expected)
                cid=col.db.scalar('select id from cards order by id limit 1')
                c=col.get_card(cid)
                c.type=2;c.queue=2;c.ivl=12;c.due=42;c.reps=8;c.lapses=1;c.factor=2500
                col.update_card(c)
                before=col.db.first('select type,queue,ivl,due,reps,lapses,factor from cards where id=?',cid)
                gids=set(x[0] for x in col.db.all('select guid from notes'))
                second_importer=AnkiPackageImporter(col,package);second_importer.run()
                second=col.db.scalar('select count(*) from notes')
                after=col.db.first('select type,queue,ivl,due,reps,lapses,factor from cards where id=?',cid)
                assert second==first
                assert gids==set(x[0] for x in col.db.all('select guid from notes'))
                assert before==after,(before,after)
                report.update(backend_test='passed',notes_after_first=first,notes_after_second=second,cards=card_count,stable_guids=True,review_schedule_preserved=True,scope='First import and unchanged-package re-import, using an isolated temporary collection. Not a content-change merge, desktop GUI, or mobile sync test.')
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
