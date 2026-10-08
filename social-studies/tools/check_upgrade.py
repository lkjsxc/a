"""Verify the previous release -> expanded APKG without using any learner data."""
from __future__ import annotations
import evidence
import sqlite3
import sys
import zipfile
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

BASE='0e70b2196f1ecbc2bdbbcf0b41d0a5943a5bc10b'


def run(root: Path) -> dict:
    from anki.collection import Collection, ImportAnkiPackageOptions, ImportAnkiPackageRequest
    from anki.lang import set_lang
    set_lang('en_US')
    package=root/'anki/social-studies.apkg'
    report={**evidence.inputs(root),'status':'running','baseline_commit':BASE,'desktop_gui_tested':False,'mobile_sync_tested':False}
    evidence.write(root,'ANKI_UPGRADE_TEST.json',report)
    if '--baseline-apkg' in sys.argv:
        raw=Path(sys.argv[sys.argv.index('--baseline-apkg')+1]).read_bytes()
    else:
        probe=subprocess.run(['git','cat-file','-e',BASE+':social-studies/anki/social-studies.apkg'],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if probe.returncode:
            report.update(status='not_run_baseline_unavailable',reason='Requires repository baseline commit or --baseline-apkg PATH')
            evidence.write(root,'ANKI_UPGRADE_TEST.json',report)
            return report
        raw=subprocess.check_output(['git','show',BASE+':social-studies/anki/social-studies.apkg'],cwd=root)
    with tempfile.TemporaryDirectory(prefix='social-previous-edition-') as tmp:
        previous=Path(tmp)/'previous.apkg';previous.write_bytes(raw)
        col=Collection(str(Path(tmp)/'upgrade.anki2'))
        try:
            def load(p: Path):
                return col.import_anki_package(ImportAnkiPackageRequest(package_path=str(p),options=ImportAnkiPackageOptions(with_scheduling=False,with_deck_configs=False)))
            load(previous)
            old={row[2].split('\x1f')[0]:(row[0],row[1]) for row in col.db.all('SELECT id,guid,flds FROM notes')}
            assert len(old)==1293, len(old)
            old_fields={r[0]:r[1] for r in col.db.all('SELECT guid,flds FROM notes')}
            old_models={r[0]:r[1] for r in col.db.all('SELECT guid,mid FROM notes')}
            dbpath=Path(tmp)/'expected.anki2'
            with zipfile.ZipFile(package) as z:dbpath.write_bytes(z.read('collection.anki2'))
            with sqlite3.connect(dbpath) as db:
                expected={r[0]:r[1] for r in db.execute('SELECT guid,flds FROM notes')}
            changed={guid for guid,fields in old_fields.items() if fields!=expected[guid]}
            assert changed, 'Expected actual editorial corrections to existing notes'
            selected=[]
            for prefix in ('F','G','H','C','P'):
                keys=sorted(key for key in old if key.startswith(prefix))
                for key in (keys[0],keys[-1]):
                    nid=old[key][0]
                    cid=col.db.scalar('SELECT id FROM cards WHERE nid=?',nid)
                    card=col.get_card(cid);card.type=2;card.queue=2;card.ivl=17;card.due=45;card.reps=9;card.lapses=2;card.factor=2550
                    col.update_card(card)
                    state=tuple(col.db.first('SELECT type,queue,ivl,due,reps,lapses,factor FROM cards WHERE id=?',cid))
                    selected.append((key,cid,state))
            load(package)
            new={row[2].split('\x1f')[0]:(row[0],row[1]) for row in col.db.all('SELECT id,guid,flds FROM notes')}
            assert len(new)==2105,len(new)
            assert dict(col.db.all('SELECT guid,flds FROM notes'))==expected, 'Actual edition content was not updated'
            assert all(col.db.scalar('SELECT mid FROM notes WHERE guid=?',guid)==mid for guid,mid in old_models.items())
            for cid in col.db.list('SELECT id FROM cards'):
                card=col.get_card(cid);note=card.note()
                assert note.fields[0] not in card.question()
                assert all(token not in card.question()+card.answer() for token in ('単元::','優先::','入試ポイント','【歴史】'))
            assert all(new.get(key)==value for key,value in old.items()),'Old note identity changed'
            assert len(set(new)-set(old))==812
            assert col.db.scalar('SELECT count(*) FROM cards')==2105
            for key,cid,state in selected:
                assert tuple(col.db.first('SELECT type,queue,ivl,due,reps,lapses,factor FROM cards WHERE id=?',cid))==state, key
            load(package)
            assert col.db.scalar('SELECT count(*) FROM notes')==2105
            assert dict(col.db.all('SELECT guid,flds FROM notes'))==expected
            for key,cid,state in selected:
                assert tuple(col.db.first('SELECT type,queue,ivl,due,reps,lapses,factor FROM cards WHERE id=?',cid))==state,key
            report.update(status='passed',existing_notes_content_updated=len(changed),all_imported_fields_match_package=True,note_types_preserved=True,all_rendered_card_faces_checked=True,old_notes=len(old),new_notes=len(new),new_only_notes=812,all_old_guids_and_note_ids_preserved=True,review_state_samples=len(selected),review_state_preserved=True,reimport_without_duplicates=True,baseline_apkg_sha256=hashlib.sha256(raw).hexdigest(),current_apkg_sha256=hashlib.sha256(package.read_bytes()).hexdigest())
        finally:
            col.close()
    (root/'ANKI_UPGRADE_TEST.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report

if __name__=='__main__':
    print(json.dumps(run(Path(__file__).resolve().parents[1]),ensure_ascii=False,indent=2))
