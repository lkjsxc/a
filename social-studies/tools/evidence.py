"""Content-addressed build inputs, independent of Git history or working directory."""
import hashlib
import json
from pathlib import Path

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def inputs(root):
    files=sorted(p for folder in ('source','tools') for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    hashes={str(p.relative_to(root)):sha256(p) for p in files}
    for local, canonical in [('ruby-policy.json','ruby.json'),('baseline-20261008.json','social-baseline-20261008.json')]:
        p=root.parent/'editorial'/canonical
        if not p.exists():p=root/local
        hashes[local]=sha256(p)
    hashes['requirements.txt']=sha256(root/'requirements.txt')
    tree=hashlib.sha256(json.dumps(hashes,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'input_tree_sha256':tree,'input_sha256':hashes}

def write(root, name, report):
    (root/name).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def invalidate(root):
    proof=inputs(root)
    for name in ('BUILD_REPORT.json','ANKI_IMPORT_TEST.json','ANKI_UPGRADE_TEST.json','BROWSER_TEST.json'):
        write(root,name,dict(status='not_run_for_this_build',backend_test='not_run_for_this_build',**proof))
    (root/'QA_REPORT.md').write_text('# 検証記録\n\nこの生成の検証は未完了です。BUILD_REPORT.jsonを参照してください。\n',encoding='utf-8')
    return proof
