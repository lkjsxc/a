#!/usr/bin/env python3
"""Build original Japanese social-studies resources from reviewed, editable sources.

Run from any directory: python social-studies/tools/build.py
Dependencies are in requirements.txt. Downloads only public-domain map outlines.
No account data, credentials, installed fonts, or unrelated files enter the package.
"""
from __future__ import annotations
import collections
import csv
import hashlib
import html
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import unicodedata
import zipfile

import evidence
import genanki
from expansion import apply_extensions, comparison
import markdown
from make_assets import PREFECTURES, CLIMATE, generate as make_assets

ROOT=Path(__file__).resolve().parents[1]
SUBJECTS={'foundation':'基礎','geography':'地理','history':'歴史','civics':'公民'}
SUBJECT_ORDER=list(SUBJECTS)
REVIEW_DATE='2026-09-30'
REVISION_DATE='2026-10-08'
MODEL_ID=1656926029
DECK_IDS={name:1656926100+i for i,name in enumerate(SUBJECT_ORDER+['atlas'])}


def save(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text.rstrip()+'\n',encoding='utf-8')


def parse_sources() -> list[dict]:
    lessons=[]
    for path in sorted((ROOT/'source').glob('*.txt')):
        lesson=None; mode=''
        for line_number,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
            if line.startswith('@lesson '):
                if lesson is not None: raise ValueError(f'{path}:{line_number}: unclosed lesson')
                fields=line[8:].split('|')
                if len(fields)!=6: raise ValueError(f'{path}:{line_number}: malformed lesson')
                lid,title,subject,year,pre,sources=fields
                lesson=dict(id=lid,title=title,subject=subject,year=year,prerequisites=[] if pre=='-' else pre.split(','),sources=sources.split(','),text=[],cards=[],questions=[])
            elif line in ('@text','@cards','@questions'):mode=line[1:]
            elif line=='@end':
                if not lesson: raise ValueError('Unexpected @end')
                # Each authored non-heading line is a paragraph, not a forced line break.
                lesson['text']='\n\n'.join(lesson['text']).strip()
                lessons.append(lesson);lesson=None;mode=''
            elif line.startswith('@'):raise ValueError(f'Unknown directive {path}:{line_number}: {line}')
            elif line.strip():
                if lesson is None:raise ValueError(f'Text outside a lesson: {path}:{line_number}')
                if mode=='text':lesson['text'].append(line)
                elif mode=='cards':
                    fields=line.split('|')
                    if len(fields)!=7:raise ValueError(f'Malformed card {path}:{line_number}')
                    no,level,front,reading,definition,point,related=fields
                    lesson['cards'].append(dict(id=f'{lesson["id"]}-{no}',level=level,front=front,reading=reading,definition=definition,point=point,related=related,lesson=lesson['id'],subject=lesson['subject'],year=lesson['year']))
                elif mode=='questions':
                    fields=line.split('|')
                    if len(fields)!=6:raise ValueError(f'Malformed question {path}:{line_number}')
                    no,level,kind,q,a,explanation=fields
                    lesson['questions'].append(dict(id=f'{lesson["id"]}-Q{no}',level=level,kind=kind,q=q,a=a,explanation=explanation))
                else:raise ValueError('Missing section')
        if lesson is not None:raise ValueError(f'Unclosed lesson in {path}')
    return lessons


def validate(lessons: list[dict], refs: dict, exams: dict) -> None:
    ids=[x['id'] for x in lessons]
    expected=[f'F{i:02}' for i in range(1,5)]+[f'G{i:02}' for i in range(1,28)]+[f'H{i:02}' for i in range(1,28)]+[f'C{i:02}' for i in range(1,19)]
    assert ids==expected,('Lesson set/order mismatch',ids)
    cards=[c for x in lessons for c in x['cards']]
    assert len({c['id'] for c in cards})==len(cards),'Duplicate stable note ID'
    fronts=collections.Counter(unicodedata.normalize('NFKC',c['front']).strip() for c in cards)
    assert not [f for f,n in fronts.items() if n>1],('Duplicate keyword',[(f,n) for f,n in fronts.items() if n>1])
    graph={x['id']:x['prerequisites'] for x in lessons}
    def visit(lid,trail):
        assert lid not in trail,('Prerequisite cycle',trail,lid)
        for p in graph[lid]:
            assert p in graph,('Missing prerequisite',lid,p)
            visit(p,trail+[lid])
    for lesson in lessons:
        assert lesson['subject'] in SUBJECTS
        assert len(lesson['text'])>=300,('Very short lesson',lesson['id'])
        assert len(lesson['cards'])>=10
        expected_questions=6
        assert len(lesson['questions'])==expected_questions,(lesson['id'],'question count')
        assert {q['id'] for q in lesson['questions']}=={f'{lesson["id"]}-Q{i:02}' for i in range(1,7)}
        assert len({c['id'] for c in lesson['cards']})==len(lesson['cards'])
        for source in lesson['sources']:assert source in refs['sources'],('Missing source',lesson['id'],source)
        visit(lesson['id'],[])
        for card in lesson['cards']:
            assert card['level'] in ('S','A')
            assert all(card[k] for k in ('front','definition','point','related'))
            assert '\t' not in card['front'] and '\n' not in card['front']
            assert '入試ポイント' not in card['point']
        for q in lesson['questions']:assert q['level'] in ('S','A') and q['q'] and q['a'] and q['explanation']
    assert len(exams['exams'])==3
    for exam in exams['exams']:
        assert len(exam['sections'])==6
        assert sum(q['points'] for s in exam['sections'] for q in s['questions'])==100
        assert len([q for s in exam['sections'] for q in s['questions']])==24
        for s in exam['sections']:
            for lid in s['lessons'].split(','):assert lid in graph
            for q in s['questions']:assert q['a'] and q['rubric'] and q['points']>0


def prefecture_cards() -> list[dict]:
    def region(i):
        return '北海道地方' if i==1 else '東北地方' if i<=7 else '関東地方' if i<=14 else '中部地方' if i<=23 else '近畿地方' if i<=30 else '中国地方' if i<=35 else '四国地方' if i<=39 else '九州地方（沖縄を含む）'
    result=[]
    for i,(name,reading,capital,cr,lon,lat) in enumerate(PREFECTURES,1):
        definition=f'都道府県庁所在地は{capital}。{region(i)}に位置する。'
        point='地図で位置を確かめ、海や隣接する都道府県と結び付ける。'
        if i==13:
            definition='都庁の所在地は新宿区。関東地方に位置する。'
            point='地図帳や設問では東京・東京都区部と表す場合もある。設問の表記を確認する。'
        if i==24:point='この教材では近畿地方に分類する。東海地方にも含める区分があるので、問題の地域区分を確認する。'
        result.append(dict(id=f'P{i:02}',level='S',front=name,reading=reading,definition=definition,point=point,related=capital+'・'+region(i),lesson=f'P{i:02}',subject='atlas',year='全学年'))
    return result


def ruby_dictionary(cards: list[dict]) -> dict:
    # Shared, explicitly edited vocabulary; a card's presence never makes it difficult.
    # Readings for comparisons/aliases must not be attached to a different surface word.
    policy=ROOT.parent/'editorial/ruby.json'
    if not policy.exists():policy=ROOT/'ruby-policy.json'
    return json.loads(policy.read_text(encoding='utf-8'))


class RubyHTML(HTMLParser):
    def __init__(self, vocab: dict):
        super().__init__(convert_charrefs=False)
        self.out=[];self.skip=0;self.vocab=vocab;self.seen=set()
        alternatives='|'.join(re.escape(w) for w in sorted(vocab,key=len,reverse=True))
        self.pattern=re.compile(r'(?<![一-龯々A-Za-z0-9ァ-ヶ])(?:'+alternatives+r')(?![一-龯々A-Za-z0-9ァ-ヶ])')
    def handle_starttag(self,tag,attrs):
        self.out.append(self.get_starttag_text())
        if tag in ('h1','h2','h3','h4','h5','h6','td','th','li','details','summary'):self.seen=set()
        if tag in ('ruby','code','pre','script','style'):self.skip+=1
    def handle_endtag(self,tag):
        self.out.append(f'</{tag}>')
        if tag in ('ruby','code','pre','script','style'):self.skip=max(0,self.skip-1)
        if tag in ('h1','h2','h3','h4','h5','h6','td','th','li','details','summary'):self.seen=set()
    def handle_startendtag(self,tag,attrs):self.out.append(self.get_starttag_text())
    def handle_entityref(self,name):self.out.append('&'+name+';')
    def handle_charref(self,name):self.out.append('&#'+name+';')
    def handle_data(self,data):
        if self.skip:self.out.append(data);return
        def replace(m):
            w=m[0]
            if w in self.seen:return w
            self.seen.add(w)
            return f'<ruby>{w}<rp>（</rp><rt>{html.escape(self.vocab[w])}</rt><rp>）</rp></ruby>'
        lines=[]
        for line in data.splitlines(keepends=True):
            independent=bool(re.match(r'\s*(?:#{1,6}\s|\||[-*+]\s|\d+\.\s)',line))
            if independent:self.seen=set()
            parts=re.split(r'(`[^`]*`|!?\[[^\]]*\]\([^)]*\)|https?://[^\s<>]+)',line)
            lines.append(''.join(part if i%2 else self.pattern.sub(replace,part) for i,part in enumerate(parts)))
            if independent:self.seen=set()
        self.out.append(''.join(lines))
    def handle_comment(self,data):self.out.append('<!--'+data+'-->')


def ruby(fragment: str, vocab: dict) -> str:
    # Unwrap old ruby before matching, preserving the actual word and attributes.
    fragment=re.sub(r'<ruby\b[^>]*>(.*?)</ruby>',lambda m:re.sub(r'<(rt|rp)\b[^>]*>.*?</\1>','',m[1],flags=re.S),fragment,flags=re.S)
    if not vocab:return fragment
    # HTMLParser otherwise rewrites bare ampersands (Q&A -> Q&A;) in Markdown.
    marker='\ue000'
    assert marker not in fragment
    parser=RubyHTML(vocab);parser.feed(fragment.replace('&',marker));parser.close()
    return ''.join(parser.out).replace(marker,'&')


def md_html(text: str, vocab: dict) -> str:
    fragment=ruby(markdown.markdown(text,extensions=['tables','fenced_code','sane_lists']),vocab)
    # Static print copies, rather than runtime JavaScript, support closed answers in WebKit.
    def printable(match):
        label=match[1];answer=match[2]
        return match[0]+f'<div class="print-answer"><p class="answer-label">{label}</p>{answer}</div>'
    return re.sub(r'<details>\s*<summary>(.*?)</summary>(.*?)</details>',printable,fragment,flags=re.S)


def front_html(card: dict, vocab: dict) -> str:
    text=html.escape(card['front'])
    return ruby(text,vocab)


def back_html(card: dict, vocab: dict) -> str:
    text=f'<p>{html.escape(card["definition"])}</p><p><strong>ポイント</strong><br>{html.escape(card["point"])}</p><p class="related"><strong>関連語</strong><br>{html.escape(card["related"])}</p>'
    return ruby(text,vocab)


def card_tags(card: dict) -> str:
    subject=SUBJECTS.get(card['subject'],'地図帳')
    return f'社会三年 科目::{subject} 優先::{card["level"]} 単元::{card["lesson"]} 学年::{card["year"]}'


def lesson_md(lesson: dict, byid: dict, refs: dict, vocab: dict) -> str:
    lid=lesson['id'];lines=[f'# {lid}　{lesson["title"]}',f'{SUBJECTS[lesson["subject"]]} / 配当学年の目安：{lesson["year"]}']
    if lesson['prerequisites']:
        lines += ['先に読んでおくとよい単元：'+ '、'.join(f'[{p} {byid[p]["title"]}]({p}.md)' for p in lesson['prerequisites'])]
    lines += [ruby(lesson['text'],vocab),'## ことばの確認','S：まず身に付けたい土台。A：比較・理由・条件を深める内容。','|目印|ことば|意味とポイント|','|---|---|---|']
    for c in lesson['cards']:
        lines.append(f'|{c["level"]}|{front_html(c,vocab)}|{back_html(c,vocab)}|')
    lines += ['## 確認問題']
    for i,q in enumerate(lesson['questions'],1):
        lines += [f'### {i}　{q["kind"]}',q['q'],f'<details><summary>解答と考え方</summary><p><strong>{html.escape(q["a"])}</strong></p><p>{html.escape(q["explanation"])}</p></details>']
    lines += ['## 参照・発展学習']
    for key in lesson['sources']:
        r=refs['sources'][key];lines += [f'- [{r["title"]}]({r["url"]})']
    lines += ['参照先には入口ページも含みます。本文・問題は独自に執筆したものです。','[単元一覧へ戻る](../README.md)']
    return ruby('\n\n'.join(lines).replace('|\n\n|','|\n|'),vocab)


TIMELINE=[
('紀元前4千年紀ごろ','メソポタミアで都市文明が発達','H01'),('紀元前3千年紀ごろ','エジプトの統一国家と文明','H01'),('紀元前221年','秦が中国を統一','H02'),('239年','卑弥呼が魏へ使いを送る','H03'),
('538年または552年','仏教の公伝（史料によって説が異なる）','H04'),('593年','聖徳太子が推古天皇を補佐する政治','H04'),('607年','小野妹子を隋へ派遣','H04'),('645年','大化の改新へつながる政変','H04'),('663年','白村江の戦い','H04'),('672年','壬申の乱','H04'),('701年','大宝律令','H05'),('710年','平城京へ都を移す','H05'),('743年','墾田永年私財法','H05'),('794年','平安京へ都を移す','H06'),('894年','遣唐使の派遣停止','H06'),('1086年','白河上皇の院政開始','H06'),('1167年','平清盛が太政大臣となる','H07'),('1185年','平氏滅亡、守護・地頭の設置を認められる','H07'),('1192年','源頼朝が征夷大将軍となる','H07'),('1221年','承久の乱','H07'),('1232年','御成敗式目','H07'),('1274年・1281年','元寇','H08'),('1333年','鎌倉幕府滅亡','H09'),('1338年','足利尊氏が征夷大将軍となる','H09'),('1392年','南北朝の合一','H09'),('1404年','勘合を使う日明貿易の開始','H09'),('1467年','応仁の乱の開始','H10'),('1492年','コロンブスがアメリカ大陸周辺へ到達','H11'),('1517年','ルターの宗教改革の始まり','H11'),('1543年','種子島への鉄砲伝来','H11'),('1549年','ザビエルのキリスト教布教','H11'),('1573年','室町幕府が滅ぶ','H12'),('1582年','本能寺の変','H12'),('1588年','刀狩令','H12'),('1590年','豊臣秀吉の全国統一','H12'),('1592年・1597年','秀吉の朝鮮侵略','H12'),('1600年','関ヶ原の戦い','H13'),('1603年','徳川家康が江戸幕府を開く','H13'),('1615年','大坂の陣で豊臣氏滅亡、武家諸法度など','H13'),('1635年','参勤交代の制度化','H13'),('1637〜1638年','島原・天草一揆','H14'),('1639年','ポルトガル船の来航禁止','H14'),('1641年','オランダ商館を出島へ移す','H14'),('1688〜1689年','名誉革命と権利章典','H18'),('1716年','享保の改革の開始','H16'),('1774年','解体新書刊行','H17'),('1776年','アメリカ独立宣言','H18'),('1787年','寛政の改革の開始','H16'),('1789年','フランス革命の開始','H18'),('1837年','大塩平八郎の乱','H16'),('1840〜1842年','アヘン戦争','H18'),('1841年','天保の改革の開始','H16'),('1853年','ペリー来航','H19'),('1854年','日米和親条約','H19'),('1858年','日米修好通商条約','H19'),('1866年','薩長同盟','H19'),('1867年','大政奉還、王政復古の大号令（慣用の旧暦年表）','H19'),('1868〜1869年','戊辰戦争','H19'),('1869年','版籍奉還','H20'),('1871年','廃藩置県、解放令、岩倉使節団出発','H20'),('1872年','学制、鉄道開通、富岡製糸場操業','H20'),('1873年','徴兵令、地租改正の開始','H20'),('1874年','民撰議院設立の建白書','H21'),('1875年','樺太・千島交換条約','H20'),('1876年','日朝修好条規、廃刀令など','H20'),('1877年','西南戦争','H20'),('1879年','沖縄県の設置','H20'),('1881年','国会開設の勅諭、自由党結成','H21'),('1885年','内閣制度の成立','H21'),('1889年','大日本帝国憲法発布','H21'),('1890年','最初の帝国議会、教育勅語','H21'),('1894〜1895年','日清戦争','H22'),('1894年／1899年','領事裁判権撤廃の条約署名／実施','H22'),('1901年','八幡製鉄所操業','H22'),('1902年','日英同盟','H22'),('1904〜1905年','日露戦争','H22'),('1910年','韓国併合','H22'),('1911年','関税自主権の完全回復、辛亥革命','H22'),('1914〜1918年','第一次世界大戦','H23'),('1915年','二十一か条の要求','H23'),('1917年','ロシア革命','H23'),('1918年','米騒動、原敬内閣成立','H23'),('1919年','ベルサイユ条約、三・一独立運動、五・四運動','H23'),('1920年','国際連盟発足','H23'),('1922年','全国水平社結成、ソ連成立','H23'),('1923年','関東大震災','H23'),('1925年','普通選挙法、治安維持法','H23'),('1929年','世界恐慌','H24'),('1931年','満州事変','H24'),('1932年','満州国建国、五・一五事件','H24'),('1933年／1935年','国際連盟脱退の通告／発効','H24'),('1936年','二・二六事件','H24'),('1937年','日中戦争の全面化','H24'),('1938年','国家総動員法','H24'),('1939年','第二次世界大戦開始','H24'),('1940年','日独伊三国同盟','H24'),('1941年','日本の対米英開戦','H24'),('1945年','沖縄戦、原爆投下、敗戦、国際連合成立','H24'),('1946年11月3日','日本国憲法公布','H25'),('1947年5月3日','日本国憲法施行','H25'),('1950〜1953年','朝鮮戦争（1953年は休戦）','H26'),('1951年／1952年','平和条約の調印／発効と主権回復','H25'),('1954年','自衛隊発足','H26'),('1955年','アジア・アフリカ会議、55年体制','H26'),('1956年','日ソ共同宣言、国連加盟','H26'),('1960年','日米安全保障条約改定','H26'),('1964年','東京オリンピック、東海道新幹線開業','H26'),('1965年','日韓基本条約','H26'),('1972年','沖縄復帰、日中共同声明','H26'),('1973年','第一次石油危機','H26'),('1978年','日中平和友好条約','H26'),('1985年','プラザ合意','H27'),('1989年','ベルリンの壁開放、マルタ会談','H27'),('1991年','ソ連解体','H27'),('1993年','EU発足、非自民連立政権','H27'),('1995年','阪神・淡路大震災','H27'),('2008年','世界金融危機','H27'),('2011年','東日本大震災','H27'),('2015年','SDGsとパリ協定の採択','C18')]

CSS='''.print-answer{display:none}.answer-label{font-weight:bold}*{box-sizing:border-box}body{margin:0;background:#fff;color:#20252c;overflow-wrap:anywhere;font-family:"Noto Sans CJK JP","Yu Gothic",sans-serif;line-height:1.95}header,main,footer{max-width:960px;margin:auto;padding:28px}h1,h2,h3{line-height:1.55}h1{font-size:1.9rem}h2{border-bottom:2px solid #dce0e5;padding-bottom:.4em;margin-top:2.5em}a{color:#1458a0;text-underline-offset:.2em}table{border-collapse:collapse;width:100%;font-size:.92rem;display:block;overflow:auto}th,td{border:1px solid #dce0e5;padding:.65em;vertical-align:top}th{background:#f5f6f8}p{margin:1em 0}rt{font-size:.54em}ruby{ruby-align:center}img{display:block;max-width:100%;height:auto;margin:1.5em auto;background:white}details{border:1px solid #dce0e5;border-radius:7px;padding:12px 18px;margin:1em 0}summary{cursor:pointer;font-weight:bold}article{border-top:4px solid #dce0e5;padding-top:2em;margin-top:3em}input,button{font:inherit;padding:.5em;border:1px solid #8a988d;border-radius:5px}input{box-sizing:border-box;width:100%}nav{display:grid;grid-template-columns:repeat(auto-fit,minmax(245px,1fr));gap:8px}nav a{display:block;padding:7px;background:#f5f6f8}.meta,.related{font-size:.9em} .answer-space{height:5em;border-bottom:1px dotted #777}.notice{padding:18px;background:#f5f6f8;border-left:4px solid #555e68}footer{font-size:.85em}code{overflow-wrap:anywhere}@media(max-width:600px){header,main,footer{padding:18px}body{font-size:17px}h1{font-size:1.55rem}table{font-size:.85rem}}@media print{details{display:none!important}.print-answer{display:block;border:1px solid #dce0e5;padding:12px 18px;margin:1em 0}body{background:white;color:black;font-size:10.5pt}header,main,footer{max-width:none;padding:0}nav,input,button,.no-print{display:none!important}article{break-before:page;border-top:0}h1,h2,h3{break-after:avoid}tr,img{break-inside:avoid}a{color:inherit}details{display:block}details::details-content{content-visibility:visible;display:block;height:auto}details>*{display:block!important}summary{font-size:.9em} .exam-section{break-inside:avoid}footer{break-before:page}}'''


def document(title: str, body: str, interactive: bool=False) -> str:
    # Offline documents are HTML/CSS too. Printing uses native CSS, never JavaScript.
    script=''
    return f'<!doctype html>\n<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="予備知識ゼロから学ぶ中学社会3年分。本文・確認問題・Anki・総合問題。"><title>{html.escape(title)}</title><style>{CSS}</style></head><body>{body}{script}</body></html>'


def make_anki(cards: list[dict], vocab: dict) -> dict:
    out=ROOT/'anki';out.mkdir(exist_ok=True)
    csvrows=[]
    model=genanki.Model(MODEL_ID,'lkjsxc 社会三年 Keyword v1',fields=[{'name':'ID'},{'name':'Front'},{'name':'Back'}],sort_field_index=1,templates=[{'name':'意味を思い出す','qfmt':'{{Front}}','afmt':'{{FrontSide}}<hr id="answer">{{Back}}'}],css='.card{font-family:"Noto Sans CJK JP","Yu Gothic",sans-serif;font-size:22px;line-height:1.85;text-align:left;max-width:760px;margin:20px auto;padding:12px}rt{font-size:.55em}p{margin:1em 0}.related{font-size:.88em}#answer{margin:1.2em 0}')
    decks={s:genanki.Deck(DECK_IDS[s],'社会三年::'+SUBJECTS.get(s,'地図帳')) for s in DECK_IDS}
    for c in cards:
        front=front_html(c,vocab);back=back_html(c,vocab);tags=card_tags(c)
        assert not any(x in front for x in ('【地理】','【歴史】','入試ポイント'))
        assert 'ID' not in model.templates[0]['qfmt']
        decks[c['subject']].add_note(genanki.Note(model=model,fields=[c['id'],front,back],tags=tags.split(),guid=genanki.guid_for('lkjsxc/a/social-studies/'+c['id'])))
        csvrows.append((front,back,tags))
    package=out/'social-studies.apkg'
    genanki.Package(list(decks.values())).write_to_file(str(package))
    with (out/'cards.csv').open('w',encoding='utf-8',newline='') as f:
        csv.writer(f,lineterminator='\n').writerows(csvrows)
    with (out/'cards.tsv').open('w',encoding='utf-8',newline='') as f:
        f.write('#separator:Tab\n#html:true\n#tags column:3\n#columns:Front\tBack\tTags\n')
        csv.writer(f,delimiter='\t',lineterminator='\n').writerows(csvrows)
    with (out/'notes-audit.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.writer(f,lineterminator='\n');writer.writerow(['ID','Keyword','Subject','Lesson','Priority']);writer.writerows((c['id'],c['front'],c['subject'],c['lesson'],c['level']) for c in cards)
    with (out/'cards.csv').open(encoding='utf-8',newline='') as f:
        check=list(csv.reader(f));assert check==[list(row) for row in csvrows]
    with (out/'cards.tsv').open(encoding='utf-8',newline='') as f:
        check=list(csv.reader((line for line in f if not line.startswith('#')),delimiter='\t'));assert check==[list(row) for row in csvrows]
    with zipfile.ZipFile(package) as z:
        assert z.testzip() is None
        raw=z.read('collection.anki2')
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'collection.anki2';db.write_bytes(raw)
            with sqlite3.connect(db) as con:
                assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
                nn=con.execute('SELECT count(*) FROM notes').fetchone()[0]
                nc=con.execute('SELECT count(*) FROM cards').fetchone()[0]
                ng=con.execute('SELECT count(DISTINCT guid) FROM notes').fetchone()[0]
                assert nn==nc==ng==len(cards),(nn,nc,ng,len(cards))
                fields=con.execute('SELECT flds FROM notes').fetchall()
                assert all(len(x[0].split('\x1f'))==3 for x in fields)
                assert {x[0].split('\x1f')[0] for x in fields}=={c['id'] for c in cards}
    instructions=f'''# Ankiで学ぶ

**おすすめは `social-studies.apkg` を一度だけ取り込む方法です。{len(cards):,}枚、1用語につき1枚です。**

## パッケージ

Ankiの「ファイルをインポート」などから `.apkg` を選びます。基礎・地理・歴史・公民・地図帳のサブデッキが作られます。表は用語だけ、裏は意味・ポイント・関連語です。単元名や安定IDはカード面には表示しません。

初めは本文で読んだ単元から学びます。タグ `単元::G01` や `優先::S` などで検索できます。未習のカードを一時停止し、読んだ単元を再開する方法もあります。新規カードは少数から始め、復習がたまる場合は減らしてください。

## CSV・TSVを使う場合

`cards.csv` はヘッダーなしのUTF-8・3列です。第1列を表（Front）、第2列を裏（Back）、第3列をタグへ割り当て、「フィールド内のHTMLを許可」を有効にします。**標準のBasic（表→裏の1枚）**のようなノートタイプを使います。逆向きカードも生成するタイプにすると枚数が倍になります。

`cards.tsv` は同じ内容で、先頭にAnki用の区切り・HTML・列情報を付けています。対応するAnkiでも、取り込み画面で3列の割当てを確認してください。`notes-audit.csv` は管理・点検用であり、そのまま取り込むファイルではありません。

**APKG・CSV・TSVは同じ内容の別形式です。全部を取り込むと重複する可能性があります。一つを選んでください。** 既存の `000004.json` 等と併用すると内容上重なる用語もあります。この教材は既存ノートを自動で削除・置換しません。

## 更新

APKGは用語ごとに安定したGUIDを使います。同じノートを継続して更新できるようにしていますが、Ankiの版・ノートタイプの変更・取り込み設定によって更新の扱いが変わるため、更新前にコレクションをバックアップしてください。CSVはID列を持たないため、用語やルビの変更時の一致判定に注意が必要です。学習履歴をもつノートの更新にはAPKGを優先します。

[公式：テキストファイルの取り込み](https://docs.ankiweb.net/importing/text-files.html) / [公式：パッケージの取り込み](https://docs.ankiweb.net/importing/packaged-decks.html)

ルビを表示できない環境では、括弧内の読みが出る場合があります。音声は含みません。図表は本文・地図帳・総合問題で別に練習します。
'''
    save(out/'README.md',instructions)
    instructions_html=md_html(instructions,vocab)
    save(out/'README.html',document('Ankiで学ぶ','<main><a href="../index.html">単元一覧</a>'+instructions_html+'</main>'))
    return {'notes':nn,'cards':nc,'unique_guids':ng,'csv_roundtrip':True,'tsv_roundtrip':True,'sqlite_integrity':'ok','front_template':'{{Front}}','desktop_gui_import_tested':False}


def make_mock_exams(data: dict, vocab: dict) -> None:
    for exam in data['exams']:
        eid=exam['id'];p=[f'# 総合問題 {eid}　{exam["title"]}',f'目安{exam["minutes"]}分・100点。{data["notice"]}'];a=[f'# 総合問題 {eid}　解答と採点基準','表現が模範解答と同じでなくても、意味と条件が正しければ加点します。誤りがあれば、指定された単元へ戻って読み直します。']
        for si,section in enumerate(exam['sections'],1):
            pts=sum(q['points'] for q in section['questions'])
            p += [f'## 大問{si}　{section["title"]}（{pts}点）',section['material']]
            a += [f'## 大問{si}　{section["title"]}（{pts}点）','戻る単元：'+', '.join(f'[{lid}](textbook/{lid}.md)' for lid in section['lessons'].split(','))]
            for qi,q in enumerate(section['questions'],1):
                p += [f'### 問{qi}（{q["points"]}点）',q['q'],'<div class="answer-space"></div>']
                a += [f'### 問{qi}（{q["points"]}点）',f'**解答例：** {q["a"]}',f'**採点基準：** {q["rubric"]}',f'確認する力：{q["skill"]}']
        p += ['解き終えてから、別ファイルの解答・採点基準を開いてください。',f'[解答へ](mock-{eid}-answers.md)']
        save(ROOT/f'mock-{eid}.md','\n\n'.join(p));save(ROOT/f'mock-{eid}-answers.md','\n\n'.join(a))
        save(ROOT/f'mock-{eid}.html',document(f'総合問題{eid}', '<main>'+md_html('\n\n'.join(p).replace(f'mock-{eid}-answers.md',f'mock-{eid}-answers.html'),vocab)+'</main>'))
        save(ROOT/f'mock-{eid}-answers.html',document(f'総合問題{eid}の解答','<main>'+md_html('\n\n'.join(a),vocab)+'</main>'))


def build() -> dict:
    proof=evidence.invalidate(ROOT)
    lessons=parse_sources();refs=json.loads((ROOT/'source'/'sources.json').read_text());exams=json.loads((ROOT/'source'/'assessments.json').read_text())
    apply_extensions(ROOT,lessons)
    validate(lessons,refs,exams)
    growth=comparison(ROOT,lessons)
    if growth.get('baseline_available'):
        assert 1.85 <= growth['body_ratio'] <= 2.7,growth
        assert growth['after_questions']==456 and growth['after_anki_cards']==2105,growth
    baseline=ROOT.parent/'editorial/social-baseline-20261008.json'
    if baseline.exists(): (ROOT/'baseline-20261008.json').write_bytes(baseline.read_bytes())
    save(ROOT/'EXPANSION_REPORT.json',json.dumps(growth,ensure_ascii=False,indent=2))
    base_cards=[c for l in lessons for c in l['cards']]
    existing_fronts={unicodedata.normalize('NFKC',c['front']) for c in base_cards}
    atlas_cards=prefecture_cards()
    for c in atlas_cards:
        if unicodedata.normalize('NFKC',c['front']) in existing_fronts:
            suffix,reading=('の都庁所在地','のとちょうしょざいち') if c['front']=='東京都' else ('の道庁所在地','のどうちょうしょざいち') if c['front']=='北海道' else ('の府庁所在地','のふちょうしょざいち') if c['front'].endswith('府') else ('の県庁所在地','のけんちょうしょざいち')
            c['front']+=suffix
            c['reading']+=reading
    cards=base_cards+atlas_cards
    assert len({unicodedata.normalize('NFKC',c['front']) for c in cards})==len(cards),'Atlas front duplicates a lesson keyword'
    assert len({c['id'] for c in cards})==len(cards)
    vocab=ruby_dictionary(cards)
    save(ROOT/'ruby-policy.json',json.dumps(vocab,ensure_ascii=False,indent=2)+'\n')
    assert '<ruby>殷' in ruby('殷',vocab)
    assert '<ruby>文字' not in ruby('文字',vocab)
    assert '<ruby>明' not in ruby('明治',vocab)
    assert 'href="H01.md"' in ruby('<a href="H01.md">殷</a>',vocab)
    assert not re.search(r'<ruby>[^<]*<ruby>',ruby('<ruby>殷<rt>いん</rt></ruby>',vocab))
    byid={l['id']:l for l in lessons}
    asset_report=make_assets(ROOT)
    navigation=[];articles=[];book=[];workbook=['# 単元別ワークブック','全76単元の確認問題です。解答は各単元の後にまとめています。まず問題だけを解いてください。']
    for l in lessons:
        raw=lesson_md(l,byid,refs,vocab)
        # Do not apply ruby twice: parser skips existing ruby spans.
        save(ROOT/'textbook'/f'{l["id"]}.md',raw)
        fragment=md_html(raw,vocab)
        standalone=re.sub(r'href="([FGHC]\d{2})\.md"',r'href="\1.html"',fragment).replace('href="../README.md"','href="../index.html"')
        save(ROOT/'textbook'/f'{l["id"]}.html',document(l['title'],'<main>'+standalone+'</main>',True))
        # Rebase per-lesson relative links for the all-in-one document.
        fragment=re.sub(r'href="([FGHC]\d{2})\.md"',r'href="#\1"',fragment).replace('href="../README.md"','href="#contents"')
        articles.append(f'<article id="{l["id"]}" data-lesson="{l["id"]}">{fragment}</article>')
        navigation.append(f'<a href="#{l["id"]}">{l["id"]} {html.escape(l["title"])}</a>')
        combined=re.sub(r'\]\(([FGHC]\d{2})\.md\)',r'](textbook/\1.md)',raw).replace('../README.md','README.md')
        book.append(combined)
        workbook += [f'## {l["id"]}　{l["title"]}']
        for i,q in enumerate(l['questions'],1):workbook += [f'### 問{i}　{q["kind"]}',q['q']]
        workbook += [f'<details><summary>{l["id"]}の解答</summary>']
        for i,q in enumerate(l['questions'],1):workbook += [f'<p><strong>問{i}　{html.escape(q["a"])}</strong><br>{html.escape(q["explanation"])}</p>']
        workbook += ['</details>']
    save(ROOT/'textbook.md','\n\n---\n\n'.join(book))
    save(ROOT/'workbook.md','\n\n'.join(workbook))
    save(ROOT/'workbook.html',document('単元別ワークブック','<main>'+md_html('\n\n'.join(workbook),vocab)+'</main>',True))
    handbook=(ROOT/'source'/'handbook.md').read_text();save(ROOT/'study-guide.md',handbook)
    save(ROOT/'study-guide.html',document('学び方と資料の読み方','<main>'+md_html(handbook,vocab)+'</main>',True))
    atlas=['# 地図帳・47都道府県','位置を先に確かめてから名称と所在地を覚えます。番号はJISの順序に対応します。','![世界の概略図](assets/world.svg)','![都道府県の概略図](assets/japan-prefectures.svg)','|番号|都道府県|都道府県庁所在地|','|---|---|---|']
    for i,(name,r,capital,cr,*_) in enumerate(PREFECTURES,1):atlas.append(f'|{i:02}|{ruby(html.escape(name),vocab)}|{ruby(html.escape(capital),vocab)}|')
    atlas += ['','東京都は都庁の所在地として新宿区を記載しています。学校の地図帳・設問では東京や東京都区部と表す場合もあります。三重県はこの教材では近畿地方ですが、東海地方にも含める区分があります。','図は位置学習用の概略図です。世界図の面積、各拡大図相互の距離・面積は直接比較できません。一部の離島を省略し、境界は領有権の主張を示しません。','## 地図を使う練習','1. 都道府県名の列を隠し、番号の位置から名前を答えます。','2. 所在地の列を隠し、名称を答えます。','3. 県名を一つ選び、地方、近くの海、隣接県、関連する産業・気候を説明します。','4. 世界図では、大陸・海洋、主な国の位置、気候や産業とのつながりを本文へ戻って確認します。','原図：[Natural Earth](https://www.naturalearthdata.com/)（public domain）。都道府県の位置や地形を詳しく調べるときは[地理院地図](https://maps.gsi.go.jp/)を使います。']
    save(ROOT/'atlas.md','\n'.join(atlas));save(ROOT/'atlas.html',document('地図帳','<main>'+md_html('\n'.join(atlas),vocab)+'</main>'))
    timeline=['# 通史年表','年代は出来事の前後を確かめるために使います。開始年・署名年・実施年の違いに注意してください。古い時代の始まりには研究上の幅があり、明治初期までの年表には旧暦の慣用表記も含まれます。','|年・時期|出来事|戻る単元|','|---|---|---|']
    for year,event,lid in TIMELINE:
        assert lid in byid
        timeline.append(f'|{year}|{event}|[{lid}](textbook/{lid}.md)|')
    save(ROOT/'timeline.md','\n'.join(timeline))
    glossary=['# 用語索引','読みの順で並べています。読みが未設定の比較項目などは表記順です。','|ことば|戻る場所|','|---|---|']
    for c in sorted(cards,key=lambda x:unicodedata.normalize('NFKC',x['reading'] if x['reading']!='-' else x['front'])):
        target='atlas.md' if c['subject']=='atlas' else f'textbook/{c["lesson"]}.md'
        glossary.append(f'|{front_html(c,vocab)}|[{c["lesson"]}]({target})|')
    save(ROOT/'glossary.md','\n'.join(glossary))
    source_lines=['# 出典・参照先と更新方針',f'内容の確認基準日：{refs["review_date"]}',refs['scope'],refs['revision_policy']]
    for key,r in refs['sources'].items():
        source_lines += [f'## {key}　{r["title"]}',f'[{r["title"]}]({r["url"]})',r.get('note','')]
        if r.get('detail_url'):source_lines.append(f'[詳しい資料]({r["detail_url"]})')
    source_lines += ['## 地図の原図','[Natural Earth](https://www.naturalearthdata.com/about/terms-of-use/)のpublic-domainデータを加工。地図の表現は、特定の国家の領有権の主張を示すものではありません。','## 発展学習・取り込み方法']
    for r in refs['further_study']:source_lines.append(f'- [{r["title"]}]({r["url"]})：{r["note"]}')
    source_lines += ['## 今回確認した補足資料（2026年9月30日）', '[GDP・実質GDP（日本銀行）](https://www.boj.or.jp/about/education/oshiete/glossary/economy/e03.htm) / [公開市場操作（日本銀行）](https://www.boj.or.jp/about/education/oshiete/seisaku/b34.htm)', '[直接請求制度（岡山市）](https://www.city.okayama.jp/shisei/0000077967.html) / [事務監査と住民監査の区別（松江市）](https://www.city.matsue.lg.jp/soshikikarasagasu/kansaiinjimukyoku/kansa/1/3669.html)', '[地図記号一覧（国土地理院）](https://www.gsi.go.jp/kohokocho/map-sign-tizukigou-2022-itiran.html) / [庭園文化（京都市）](https://kyoto-museums.city.kyoto.lg.jp/feature-column/gardens/)', '[NPTの概要（外務省）](https://www.mofa.go.jp/mofaj/gaiko/kaku/npt/gaiyo.html) / [非核三原則に関する歴史的な国会決議（外務省）](https://www.mofa.go.jp/mofaj/gaiko/kaku/gensoku/ketsugi.html)', '[Anki公式マニュアル：APKG更新](https://docs.ankiweb.net/importing/packaged-decks.html) / [Anki旧取り込みAPIの変更記録](https://github.com/ankitects/anki/issues/5307)', '上記と憲法条文などの重要な制度を確認しました。全リンク先の全文章を逐語的に照合したとの意味ではなく、専門家の独立査読・入試難易度の標準化は未実施です。']
    source_lines += ['## 2026年10月8日の増補', '地理・歴史・公民の追加本文には、制度や資料の解説へのリンクを付けています。初版の全情報を同日に再確認したものではありません。新しい数値問題は学習用の架空例です。', '[追加原稿と参照リンクの一覧](expansion-sources.md)', '基礎4単元も定義・仕組み・具体例を説明する文体へ改稿し、各6問を収録しました。']
    save(ROOT/'SOURCES.md','\n\n'.join(source_lines))
    coverage=['# 範囲と単元の対応','中学校学習指導要領解説・社会編の地理的・歴史的・公民的分野を参照した、教材独自の対応表です。学校・教科書ごとの配当順とは異なる場合があります。全教科書の全細目を一対一で照合した表ではありません。','|ID|分野|単元|学年目安|用語|確認問題|','|---|---|---|---|---:|---:|']
    for l in lessons:coverage.append(f'|{l["id"]}|{SUBJECTS[l["subject"]]}|[{l["title"]}](textbook/{l["id"]}.md)|{l["year"]}|{len(l["cards"])}|{len(l["questions"])}|')
    save(ROOT/'coverage.md','\n'.join(coverage))
    reference_lines=['# 増補原稿と関連資料', '増補日：2026年10月8日。72単元の追加本文の参照リンクです。各資料は関連する事項を確認するためのもので、追加本文の全記述を一つの資料だけで裏付けるものではありません。', '原稿・問題は独自執筆です。政策の現在の数値や手続きは、必要に応じて最新の公的案内を確認してください。']
    for extra in sorted((ROOT/'source'/'expansion').glob('*.txt')):
        lids=re.findall(r'^@extend (\w+)$',extra.read_text(),re.M)
        reference_lines += ['## '+extra.stem, '本文：'+ ' / '.join(f'[{lid} {byid[lid]["title"]}](textbook/{lid}.md)' for lid in lids)]
        for label,url in re.findall(r'\[([^\]]+)\]\((https?://[^)]+)\)',extra.read_text()):
            reference_lines.append('- ['+label+']('+url+')')
    save(ROOT/'expansion-sources.md','\n\n'.join(reference_lines))
    anki_report=make_anki(cards,vocab);make_mock_exams(exams,vocab)
    stats={'lessons':len(lessons),'lesson_counts':dict(collections.Counter(x['subject'] for x in lessons)),'lesson_cards':sum(len(x['cards']) for x in lessons),'atlas_cards':47,'anki_cards':len(cards),'lesson_questions':sum(len(x['questions']) for x in lessons),'worked_examples':12,'mock_exams':3,'mock_questions':72,'timeline_entries':len(TIMELINE),'reading_characters':growth['after_body_characters']}
    for stem in ('timeline','glossary','SOURCES','coverage','expansion-sources'):
        text=(ROOT/(stem+'.md')).read_text()
        fragment=md_html(text,vocab)
        fragment=re.sub(r'href="textbook/([FGHC]\d{2})\.md"',r'href="textbook/\1.html"',fragment).replace('href="atlas.md"','href="atlas.html"').replace('href="expansion-sources.md"','href="expansion-sources.html"')
        save(ROOT/(stem+'.html'),document(stem,'<main><a href="index.html">単元一覧</a>'+fragment+'</main>'))
    header=f'<header><p class="meta">中学校3年間の社会・増補日 {REVISION_DATE} / 初版確認基準日 {REVIEW_DATE}</p><h1>中学社会</h1><p>地理・歴史・公民の本文、確認問題、資料を掲載しています。</p><p>{len(lessons)}単元 / {len(cards):,}枚のAnki / 確認問題{stats["lesson_questions"]}問 / 総合問題3回</p><p class="notice">初めて使うときは<a href="study-guide.html">学び方と資料の読み方</a>から。得点と偏差値を直接換算できる教材ではありません。</p><p><a href="atlas.html">地図帳</a>　<a href="workbook.html">確認問題</a>　<a href="anki/README.html">Anki</a>　<a href="timeline.html">年表</a></p><p><a href="mock-01.html">総合問題1</a>　<a href="mock-02.html">総合問題2</a>　<a href="mock-03.html">総合問題3</a></p><h2 id="contents">単元一覧</h2><nav>'+''.join(navigation)+'</nav></header>'
    save(ROOT/'index.html',document('中学社会 — 中学社会3年間',header+'<main>'+''.join(articles)+'</main><footer>本文・問題は独自作成。<a href="SOURCES.html">出典と更新方針</a> / <a href="QA_REPORT.md">検証記録</a>。HTMLは展開後、ネット接続なしで読めます。ブラウザーの印刷で紙へ出力できます。</footer>',True))
    readme=f'''# 中学社会

中学校3年間の地理・歴史・公民の教材です。基礎知識から高校受験の確認問題まで、本文・用語・地図・資料・記述問題を掲載しています。**特定の偏差値や合格を保証するものではありません。**

## 最初に開く

**[学び方・12の解き方・比較表](study-guide.md)** → 基礎F01〜F04 → 地理・歴史 → 公民。

[全教材のZIP](downloads/social-studies-complete.zip)を展開し、`index.html`を開くとオフラインで読めます。オンライン版は[社会の目次](https://lkjsxc.github.io/a/social-studies/)から利用できます。いずれもHTMLとCSSで構成され、検索・ブックマーク・印刷にはブラウザーの標準機能を使用します。

## 増補版（2026年10月8日）

地理27・歴史27・公民18の72単元に、追加の本文・用語・比較問題を収録しました。既存カードのID・表の語句を保ち、必要な定義の訂正と基礎の改稿を反映しています。逆向きカードの複製による枚数の増加ではありません。本文量は同じ数え方で約{growth['body_ratio']:.2f}倍、単元問題は{growth['before_questions']}問から{growth['after_questions']}問、Ankiは{growth['before_anki_cards']:,}枚から{growth['after_anki_cards']:,}枚です。カード枚数は約1.6倍であり、全項目を一律に倍増したものではありません。

基礎4単元は、資料・計算・地図・史料の定義と具体例を説明する文体へ改稿しました。[増補の比較記録](EXPANSION_REPORT.json)には適用した範囲を区別して記録しています。

## 内容

|教材|内容・入口|
|---|---|
|本文|**76単元**（基礎4・地理27・歴史27・公民18）。[一冊のMarkdown](textbook.md) / [範囲の対応表](coverage.md)|
|Anki|**{len(cards):,}枚**（本文{stats['lesson_cards']:,}＋都道府県47）。[APKG](anki/social-studies.apkg) / [CSV](anki/cards.csv) / [TSV](anki/cards.tsv) / [取り込み説明](anki/README.md)|
|確認問題|**{stats['lesson_questions']}問**。[単元別ワークブック](workbook.md)。各本文にも解答付きで収録|
|総合問題|独自問題3回、各50分・100点、計72問。[第1回](mock-01.md) / [第2回](mock-02.md) / [第3回](mock-03.md)|
|採点|[第1回解答](mock-01-answers.md) / [第2回解答](mock-02-answers.md) / [第3回解答](mock-03-answers.md)。記述には部分点の基準あり|
|地図と整理|[世界・47都道府県の地図帳](atlas.md) / [{len(TIMELINE)}項目の通史年表](timeline.md) / [用語索引](glossary.md)|
|出典と品質|[参照先・更新方針](SOURCES.md) / [検証記録](QA_REPORT.md)|

Ankiの表は用語だけ、裏は意味・ポイント・関連語です。難しい地名・人名・制度名などへ選択的にルビを付けています。科目・単元・優先度のタグは管理用で、カードの表へ見出しとして追加しません。

**APKG・CSV・TSVは同じ内容です。一つだけ取り込んでください。** 既存のリポジトリの教材や学習履歴は削除しません。以前の社会カードと併用すると、同じ内容の用語が含まれる場合があります。

## 単元
'''
    for subject in SUBJECT_ORDER:
        readme+=f'\n### {SUBJECTS[subject]}\n\n'
        readme+='\n'.join(f'- [{l["id"]}　{l["title"]}](textbook/{l["id"]}.md)' for l in lessons if l['subject']==subject)+'\n'
    readme+='''
## 編集・再生成

以下は編集者向けの手順です。閲覧・Anki利用にPythonやNode.jsは不要です。リポジトリまたはZIP内の`social-studies`を親ディレクトリに置いて実行します。`source/`が編集する原稿、`tools/`が生成処理です。本文、カード、確認問題を同じ原稿から生成します。

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r social-studies/requirements.txt
python social-studies/tools/build.py
```

検証済みパッケージを作る場合は、追加で `anki` と `playwright` をインストールし、`python -m playwright install chromium` の後に `python social-studies/tools/build.py --verify-anki --verify-render` を実行します。今回の検証環境は `anki 26.9.3`、`playwright 1.63.0` です。これらは利用者が教材を読むための依存関係ではありません。

ZIPには変更しない比較基準`baseline-20261008.json`とルビ辞書を同梱します。Git履歴なしでも教材生成・新規Anki取り込み・表示検査を再現できます。旧版からの更新試験はリポジトリの旧コミット、または`--baseline-apkg PATH`で指定する旧版APKGが必要です。

初回はNatural Earthのpublic-domain地図データを取得します。ネットワークが必要なのはこの地図取得で、生成後のHTMLとAnkiの学習にネット接続は不要です。地図キャッシュはホームディレクトリの `.cache/social-studies-naturalearth/` に保存し、配布物へ含めません。

本文の修正では既存カードIDを保ちます。APKGのノートGUIDはIDから決まり、内容と無関係に毎回新しく作り直すことを避けています。元の数字・計算条件を変えたときは、解答・採点基準・検証も見直します。

## ライセンスと注意

オリジナルの本文・問題・生成コードはリポジトリの[Apache License 2.0](LICENSE)に従います。加工した地図の原図はNatural Earthのpublic-domainデータです。参照先の資料を丸ごと転載したものではなく、参照先の著作物にはそれぞれの条件が適用されます。フォントファイル、個人の学習履歴、音声は配布しません。

初版の内容確認基準日は2026年9月30日、地理・歴史・公民の増補日は2026年10月8日です。追加部分は関連する公的資料などを確認していますが、初版の全記述を同日に逐語的に再検証したという意味ではありません。制度・統計・入試の実際の手続きは、必要に応じ最新の公式資料で確認します。架空の数値を実測値として引用しないでください。外部の教員や試験団体による査読・難易度標準化を受けた教材ではありません。
'''
    save(ROOT/'README.md',readme)
    if (ROOT.parent/'LICENSE').exists(): (ROOT/'LICENSE').write_bytes((ROOT.parent/'LICENSE').read_bytes())
    # Arithmetic properties used repeatedly throughout the materials.
    assert 800000/400==2000 and 200*.4==80 and 100*.6==60
    assert (45-50)/50*100==-10 and 35-20==15
    assert 4*25000/100/1000==1 and (135-15)/15==8
    assert 300*2/3==200 and 240*2/3==160
    assert 100*.1+50*.2==20 and 1800*12-20000==1600
    assert 6_000_000/30_000==200 and 8_000_000/32_000==250
    assert 45*.4==18 and 110*.25==27.5
    assert sum(CLIMATE['A']['rain'])>sum(CLIMATE['B']['rain'])
    report={'status':'running',**proof,'review_date':REVIEW_DATE,'revision_date':REVISION_DATE,'expansion':growth,'statistics':stats,'anki':anki_report,'maps':asset_report,'checks':['76 expected lessons and order','unique lesson/card identifiers and normalized keywords','prerequisite references and acyclic graph','source reference IDs resolved','6 questions per lesson across all 76 lessons','3 assessments x 24 questions; each exactly 100 points','CSV/TSV exact round-trip including HTML and tags','APKG ZIP CRC and SQLite integrity; note/card/GUID counts','keyword-only question template','ruby boundary and nesting regression checks','worked arithmetic and mock-exam numerical spot checks'],'limitations':['No desktop/mobile Anki GUI import or synchronization was tested by this builder.','No external subject-expert peer review or exam-score standardization.','URL listings include reference landing pages, not per-sentence evidence or a guarantee of future availability.','No PDF is generated. Print the offline HTML or use the Markdown files.']}
    save(ROOT/'BUILD_REPORT.json',json.dumps(report,ensure_ascii=False,indent=2))
    if '--verify-anki' in sys.argv:
        import check_import
        if check_import.main()!=0:
            raise RuntimeError('Anki backend integration test failed')
        report['anki_backend']=json.loads((ROOT/'ANKI_IMPORT_TEST.json').read_text())
        import check_upgrade
        report['anki_upgrade']=check_upgrade.run(ROOT)
    else:
        save(ROOT/'ANKI_IMPORT_TEST.json',json.dumps({'backend_test':'not_run_for_this_build','artifact_sha256':hashlib.sha256((ROOT/'anki/social-studies.apkg').read_bytes()).hexdigest()},indent=2))
    if '--verify-render' in sys.argv:
        import check_render
        report['browser']=check_render.run(ROOT)
    else:
        save(ROOT/'BROWSER_TEST.json',json.dumps({'status':'not_run_for_this_build'},indent=2))
    qa=['# 検証記録',f'確認基準日：{REVIEW_DATE}','この記録は生成プログラムが実際に成功した検査と、その限界を示します。外部の専門家の査読や、模試集団での難易度調査を意味しません。','## 収録数']
    qa += [f'- {k}: {v}' for k,v in stats.items()]
    qa += ['## 増補の適用範囲', '2026年10月8日、地理・歴史・公民の72単元を増補しました。基礎4単元も改稿し、全76単元に各6問を収録しました。', '本文量は見出し・文章・本文内の参照リンクを含め、空白を除く同一基準で比較しています。カードの説明・問題・生成HTMLのタグを文字数の倍増に含めていません。', json.dumps({k:v for k,v in growth.items() if k!='lessons'},ensure_ascii=False,indent=2)]
    qa += ['## 自動検査']+[f'- {x}' for x in report['checks']]
    qa += ['## Ankiの検証範囲',f'APKG内のSQLiteデータベースを開き、ノート数・カード数・一意なGUIDがそれぞれ{len(cards):,}件で一致し、整合性検査が成功しました。CSV・TSVを再度読み込み、全フィールドの一致を確認しました。','これはデスクトップ・スマートフォンのAnki画面での操作や同期の試験ではありません。更新前にはバックアップを取り、初回は数枚を開いてルビと裏面を確認してください。','## 内容面の点検','本文では、鎖国と断交、署名と発効、公布と施行、総議員と出席議員、割合と実数、政府の立場と現実の管理などを区別して記述しています。歴史の説明を一つの原因や一人の功績だけへ単純化しないよう注意しています。','計算例・グラフの架空データを明示し、総合問題の配点合計と基本計算を確認しました。個々の文の正確さを自動検査だけで保証することはできません。誤りや読みにくさが見つかった場合は、原稿を直して再生成してください。','## 地図',json.dumps(asset_report,ensure_ascii=False),'原図を47都道府県のコードで抽出したことを検査しています。地図は位置学習用で、一部の離島を省略します。国境・領有権の厳密な判断の資料には用いません。','## 配布形式','Markdown・オフラインHTML・APKG・CSV・TSV・ZIPを生成します。PDFは含みません。印刷にはブラウザーの印刷機能を利用できます。フォントファイルと個人データは含みません。']
    if report.get('anki_backend',{}).get('backend_test')=='passed':
        qa += ['## Anki実装による取り込み試験', 'Anki Python '+report['anki_backend']['anki_python_version']+' の実際の取り込み処理を、個人データを含まない一時コレクションで実行しました。初回取り込み、同一APKGの再取り込み、内容変更を含む更新、試験用の復習状態の保持を検査しました。詳しい対象ファイルと結果は ANKI_IMPORT_TEST.json に記録しています。デスクトップ画面・実機スマートフォン・同期の試験ではありません。']
    if report.get('browser',{}).get('status')=='passed':
        qa += ['## ブラウザー表示試験', 'Chromiumでデスクトップ幅・スマートフォン幅を確認し、単元数、表、スクリプトがないこと、解答の開閉、画像読込、横方向のはみ出し、印刷時の解答表示を検査しました。実機のSafariやAnkiアプリの画面を試験したものではありません。詳細は BROWSER_TEST.json にあります。']
    save(ROOT/'QA_REPORT.md','\n\n'.join(qa))
    if report.get('anki_upgrade',{}).get('status')=='passed':
        save(ROOT/'QA_REPORT.md',(ROOT/'QA_REPORT.md').read_text()+'\n\n## 旧版から増補版への取り込み\n旧版1,293ノートから増補版2,105ノートへの取り込みを、個人データを含まない一時コレクションで検証しました。既存ノートの全ID・GUIDの保持、812件の追加、10枚の試験用復習状態の保持、再取り込みによる重複がないことを確認しました。詳細は ANKI_UPGRADE_TEST.json を参照してください。')
    # Verify all generated local links point to an existing file; anchors stay within HTML.
    missing=[]
    for p in ROOT.rglob('*'):
        if p.suffix not in ('.md','.html') or 'source' in p.relative_to(ROOT).parts:continue
        text=p.read_text(encoding='utf-8')
        links=re.findall(r'(?:href|src)="([^"]+)"',text) if p.suffix=='.html' else re.findall(r'\]\(([^)]+)\)',text)
        for link in links:
            if '://' in link or link.startswith(('#','mailto:')):continue
            target=link.split('#')[0]
            if target=='downloads/social-studies-complete.zip':continue # created below
            if target and not (p.parent/html.unescape(target)).exists():missing.append((str(p.relative_to(ROOT)),link))
    assert not missing,('Broken local links',missing[:20])
    report['checks'].append('all generated local file/image links resolved')
    report['status']='passed'
    report['artifact_sha256']={str(p.relative_to(ROOT)):evidence.sha256(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.suffix in ('.html','.md','.apkg','.csv','.tsv','.svg') and not any(x in p.relative_to(ROOT).parts for x in ('source','tools','downloads')) and p.name!='QA_REPORT.md'}
    save(ROOT/'BUILD_REPORT.json',json.dumps(report,ensure_ascii=False,indent=2))
    save(ROOT/'QA_REPORT.md',(ROOT/'QA_REPORT.md').read_text()+'\n\n生成済みのローカルファイル・画像リンクについて、参照先の存在を検査して成功しました。')
    package_dir=ROOT/'downloads';package_dir.mkdir(exist_ok=True)
    files=[p for p in sorted(ROOT.rglob('*')) if p.is_file() and not any(x in p.relative_to(ROOT).parts for x in ('downloads','__pycache__','.venv')) and p.name!='manifest.sha256' and p.suffix not in ('.pyc',)]
    manifest='\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(ROOT)) for p in files)
    save(ROOT/'manifest.sha256',manifest);files.append(ROOT/'manifest.sha256')
    archive=package_dir/'social-studies-complete.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:
            info=zipfile.ZipInfo('social-studies/'+str(p.relative_to(ROOT)),date_time=(2026,10,8,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,p.read_bytes())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert not any(name.lower().endswith(('.ttf','.otf','.ttc','.woff','.woff2')) for name in z.namelist())
        assert 'social-studies/index.html' in z.namelist()
        assert 'social-studies/anki/social-studies.apkg' in z.namelist()
    print(json.dumps({'status':'ok','statistics':stats,'archive_bytes':archive.stat().st_size,'anki':anki_report},ensure_ascii=False,indent=2))
    return report


if __name__=='__main__':
    try:
        build()
    except Exception as exc:
        evidence.write(ROOT,'BUILD_REPORT.json',dict(status='failed',error_type=type(exc).__name__,error=str(exc),**evidence.inputs(ROOT)))
        raise
